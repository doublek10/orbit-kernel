"""
Financial Graph

The unified, immutable financial timeline described in Orbit's core
pitch: every transaction from every connected provider (and every manual
entry) lands here as one normalized record, scoped to a company. Nothing
downstream (dashboard, AI, workflows) queries `ledger_transactions`
directly - they all go through this module, so the shape of "what a
transaction looks like" only has one definition in the whole system.

Money is never mutated or deleted once written - corrections are new
transactions, same as a real ledger. That's what "immutable" means here.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import asyncpg

from kernel.rule_engine.engine import RuleEngine


@dataclass(frozen=True)
class Transaction:
    id: str
    account_id: str
    direction: str
    amount: float
    currency: str
    category: str
    counterparty: str | None
    description: str
    source: str
    is_anomaly: bool
    occurred_at: datetime

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "account_id": self.account_id,
            "direction": self.direction,
            "amount": self.amount,
            "currency": self.currency,
            "category": self.category,
            "counterparty": self.counterparty,
            "description": self.description,
            "source": self.source,
            "is_anomaly": self.is_anomaly,
            "occurred_at": self.occurred_at.isoformat(),
        }


class FinancialGraph:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
        self._rules = RuleEngine()

    async def ensure_default_account(
        self, company_id: str, *, name: str = "Primary Wallet", currency: str = "KES"
    ) -> str:
        """Get-or-create the default account for a company. Idempotent -
        safe to call on every dashboard load without creating duplicates."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM accounts WHERE company_id = $1 ORDER BY created_at ASC LIMIT 1",
                company_id,
            )
            if row is not None:
                return str(row["id"])

            row = await conn.fetchrow(
                """
                INSERT INTO accounts (company_id, name, currency, kind)
                VALUES ($1, $2, $3, 'wallet')
                RETURNING id
                """,
                company_id,
                name,
                currency,
            )
            return str(row["id"])

    async def record_transaction(
        self,
        *,
        company_id: str,
        account_id: str,
        direction: str,
        amount: float,
        currency: str = "KES",
        description: str = "",
        counterparty: str | None = None,
        category: str | None = None,
        source: str = "manual",
        connection_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> Transaction:
        if direction not in ("inflow", "outflow"):
            raise ValueError("direction must be 'inflow' or 'outflow'")

        # The Rule Engine decides categorization and anomaly detection -
        # the Financial Graph just applies the result.
        if category is None:
            result = await self._rules.evaluate(
                None, "transaction.categorize", {"description": description}
            )
            category = result.details["category"]

        recent_average = await self._recent_average_outflow(company_id)
        anomaly_result = await self._rules.evaluate(
            None,
            "transaction.anomaly",
            {"amount": amount, "recent_average": recent_average}
            if direction == "outflow"
            else {"amount": 0, "recent_average": 0},
        )

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO ledger_transactions
                    (company_id, account_id, connection_id, direction, amount, currency,
                     category, counterparty, description, source, is_anomaly, occurred_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, COALESCE($12, now()))
                RETURNING id, account_id, direction, amount, currency, category,
                          counterparty, description, source, is_anomaly, occurred_at
                """,
                company_id,
                account_id,
                connection_id,
                direction,
                amount,
                currency,
                category,
                counterparty,
                description,
                source,
                anomaly_result.details["is_anomaly"],
                occurred_at,
            )
        return self._row_to_transaction(row)

    async def timeline(self, company_id: str, *, limit: int = 50, offset: int = 0) -> list[Transaction]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, account_id, direction, amount, currency, category,
                       counterparty, description, source, is_anomaly, occurred_at
                FROM ledger_transactions
                WHERE company_id = $1
                ORDER BY occurred_at DESC
                LIMIT $2 OFFSET $3
                """,
                company_id,
                limit,
                offset,
            )
        return [self._row_to_transaction(row) for row in rows]

    async def balance_summary(self, company_id: str) -> dict:
        async with self._pool.acquire() as conn:
            totals = await conn.fetchrow(
                """
                SELECT
                    COALESCE(SUM(amount) FILTER (WHERE direction = 'inflow'), 0) AS total_in,
                    COALESCE(SUM(amount) FILTER (WHERE direction = 'outflow'), 0) AS total_out
                FROM ledger_transactions
                WHERE company_id = $1
                """,
                company_id,
            )
            window = await conn.fetchrow(
                """
                SELECT
                    COALESCE(SUM(amount) FILTER (WHERE direction = 'inflow'), 0) AS in_30d,
                    COALESCE(SUM(amount) FILTER (WHERE direction = 'outflow'), 0) AS out_30d,
                    COUNT(*) FILTER (WHERE is_anomaly) AS anomalies_30d,
                    COUNT(*) AS transactions_30d
                FROM ledger_transactions
                WHERE company_id = $1 AND occurred_at >= now() - interval '30 days'
                """,
                company_id,
            )
            currency_row = await conn.fetchrow(
                "SELECT currency FROM accounts WHERE company_id = $1 ORDER BY created_at ASC LIMIT 1",
                company_id,
            )

        balance = float(totals["total_in"]) - float(totals["total_out"])
        return {
            "balance": round(balance, 2),
            "currency": currency_row["currency"] if currency_row else "KES",
            "inflow_30d": round(float(window["in_30d"]), 2),
            "outflow_30d": round(float(window["out_30d"]), 2),
            "net_30d": round(float(window["in_30d"]) - float(window["out_30d"]), 2),
            "anomalies_30d": window["anomalies_30d"],
            "transactions_30d": window["transactions_30d"],
        }

    async def health_score(self, company_id: str) -> dict:
        """
        A transparent, explainable first version of "business health" -
        not a black box. Three signals, each worth up to ~33 points:
          - cash trend: is net cash flow over the last 30 days positive?
          - runway: how many months would the current balance cover at
            the current burn rate?
          - stability: how many anomalies showed up relative to volume?
        """
        summary = await self.balance_summary(company_id)
        score = 0.0
        signals = []

        net = summary["net_30d"]
        if net > 0:
            score += 34
            signals.append("Positive cash flow over the last 30 days")
        elif net == 0:
            score += 17
            signals.append("Cash flow is flat over the last 30 days")
        else:
            signals.append("Cash flow is negative over the last 30 days")

        monthly_burn = summary["outflow_30d"]
        runway_months = (summary["balance"] / monthly_burn) if monthly_burn > 0 else 12
        runway_score = min(33, max(0, runway_months * 33 / 6))  # 6+ months burn = full marks
        score += runway_score
        signals.append(f"Approx. {round(runway_months, 1)} months of runway at current burn rate")

        volume = max(1, summary["transactions_30d"])
        anomaly_ratio = summary["anomalies_30d"] / volume
        stability_score = max(0, 33 - anomaly_ratio * 100)
        score += stability_score
        if summary["anomalies_30d"] > 0:
            signals.append(f"{summary['anomalies_30d']} unusual transaction(s) flagged for review")
        else:
            signals.append("No unusual transactions flagged")

        score = round(min(100, max(0, score)))
        label = "strong" if score >= 70 else "watch" if score >= 40 else "at risk"

        return {"score": score, "label": label, "signals": signals}

    async def _recent_average_outflow(self, company_id: str) -> float:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COALESCE(AVG(amount), 0) AS avg_amount
                FROM ledger_transactions
                WHERE company_id = $1 AND direction = 'outflow'
                  AND occurred_at >= now() - interval '30 days'
                """,
                company_id,
            )
        return float(row["avg_amount"])

    @staticmethod
    def _row_to_transaction(row) -> Transaction:
        return Transaction(
            id=str(row["id"]),
            account_id=str(row["account_id"]),
            direction=row["direction"],
            amount=float(row["amount"]),
            currency=row["currency"],
            category=row["category"],
            counterparty=row["counterparty"],
            description=row["description"],
            source=row["source"],
            is_anomaly=row["is_anomaly"],
            occurred_at=row["occurred_at"],
        )
