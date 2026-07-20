"""
Replay - Digital Financial Twin

The README's planned approach was a copy-on-write scratch schema of the
Financial Graph. This first version reaches the same non-negotiable
guarantee - the production ledger is never written to during a
simulation - by a simpler route: it reads real historical data (current
balance, 30-day average net flow) and projects forward entirely in
memory, applying whatever hypothetical adjustments the caller supplies.
Nothing here executes a single INSERT/UPDATE/DELETE. Swap in an actual
scratch-schema copy later if simulations need to run real Workflow
automations against hypothetical data - the request/response shape
here doesn't need to change for that.
"""

from dataclasses import dataclass

import asyncpg

from financial_graph.graph import FinancialGraph

_MAX_HORIZON_DAYS = 365


@dataclass(frozen=True)
class Scenario:
    label: str
    kind: str  # "one_time" | "recurring"
    amount: float  # positive = inflow, negative = outflow
    day_offset: int = 0  # for one_time: which day it lands on
    frequency_days: int = 30  # for recurring: how often it repeats


class ReplaySimulator:
    def __init__(self, pool: asyncpg.Pool):
        self._graph = FinancialGraph(pool)

    async def simulate(self, company_id: str, *, scenarios: list[dict], horizon_days: int = 90) -> dict:
        horizon_days = max(1, min(_MAX_HORIZON_DAYS, horizon_days))
        parsed = [self._parse_scenario(s) for s in scenarios]

        summary = await self._graph.balance_summary(company_id)
        baseline_daily_net = summary["net_30d"] / 30 if summary["net_30d"] else 0.0
        balance = summary["balance"]

        series = []
        min_balance = balance
        min_balance_day = 0
        goes_negative_on: int | None = None

        for day in range(horizon_days + 1):
            if day > 0:
                balance += baseline_daily_net
                for s in parsed:
                    balance += self._scenario_delta_for_day(s, day)

            if balance < min_balance:
                min_balance = balance
                min_balance_day = day
            if balance < 0 and goes_negative_on is None:
                goes_negative_on = day

            if day % max(1, horizon_days // 30) == 0 or day == horizon_days:
                series.append({"day": day, "projected_balance": round(balance, 2)})

        return {
            "starting_balance": round(summary["balance"], 2),
            "baseline_daily_net": round(baseline_daily_net, 2),
            "horizon_days": horizon_days,
            "ending_balance": round(balance, 2),
            "min_balance": round(min_balance, 2),
            "min_balance_day": min_balance_day,
            "goes_negative_on_day": goes_negative_on,
            "series": series,
            "scenarios_applied": [s.__dict__ for s in parsed],
        }

    def _parse_scenario(self, raw: dict) -> Scenario:
        kind = raw.get("kind", "one_time")
        if kind not in ("one_time", "recurring"):
            raise ValueError("scenario kind must be 'one_time' or 'recurring'")
        return Scenario(
            label=raw.get("label", "Scenario"),
            kind=kind,
            amount=float(raw["amount"]),
            day_offset=int(raw.get("day_offset", 0)),
            frequency_days=max(1, int(raw.get("frequency_days", 30))),
        )

    def _scenario_delta_for_day(self, s: Scenario, day: int) -> float:
        if s.kind == "one_time":
            return s.amount if day == s.day_offset else 0.0
        # recurring: fires on day_offset, day_offset + frequency, ...
        if day < s.day_offset:
            return 0.0
        return s.amount if (day - s.day_offset) % s.frequency_days == 0 else 0.0
