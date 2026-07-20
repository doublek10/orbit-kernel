"""
Mock Mobile Money Adapter

Orbit's provider layer is designed so real integrations (M-Pesa, Airtel
Money, a bank's open-banking API, an accounting platform) all implement
the same `execute(operation, payload) -> dict` shape and never get
called directly by anything except the Provider Manager.

This adapter is the first concrete implementation of that interface. It
doesn't call a real mobile money API (that needs real merchant
credentials and a signed agreement) - instead it deterministically
generates a realistic transaction history for a newly-connected company,
in the shape a real Kenyan mobile money statement would take, so the
rest of the platform (Financial Graph, dashboard, health score, rule
engine) has real data to operate on end to end. Swap this module for a
live adapter later without changing any caller.
"""

import hashlib
import random
from datetime import datetime, timedelta, timezone

_COUNTERPARTIES = {
    "inflow": [
        ("Customer Till Payment", "revenue"),
        ("Customer Till Payment", "revenue"),
        ("Invoice Settlement - Acme Traders", "revenue"),
        ("Invoice Settlement - Kesho Retail", "revenue"),
    ],
    "outflow": [
        ("Supplier Payment - Jua Wholesale", "supplier"),
        ("KPLC Prepaid Token", "utilities"),
        ("Staff Salary Disbursement", "salary"),
        ("Safaricom Data Bundle", "utilities"),
        ("Rent - Westlands Office", "rent"),
        ("Fuel - Total Energies", "transport"),
        ("KRA iTax Payment", "tax"),
    ],
}


class MockMobileMoneyAdapter:
    name = "mock_mobile_money"
    display_name = "Mobile Money (Demo)"

    async def execute(self, operation: str, payload: dict) -> dict:
        if operation == "connect":
            return {
                "provider": self.name,
                "display_name": self.display_name,
                "status": "connected",
                "external_account_ref": f"MM-{payload.get('company_id', 'unknown')[:8]}",
            }
        if operation == "sync":
            currency = payload.get("currency", "KES")
            return {
                "transactions": self._generate_transactions(payload.get("company_id", ""), currency)
            }
        raise NotImplementedError(f"Operation '{operation}' not supported by {self.name}")

    def _generate_transactions(self, seed_key: str, currency: str = "KES") -> list[dict]:
        # Seeded on the company id so the same company always gets the
        # same demo history (repeatable, not random noise on every sync).
        seed = int(hashlib.sha256(seed_key.encode()).hexdigest(), 16) % (2**31)
        rng = random.Random(seed)

        now = datetime.now(timezone.utc)
        transactions = []
        for day_offset in range(30, -1, -1):
            occurred_at = now - timedelta(days=day_offset, hours=rng.randint(0, 20))
            daily_events = rng.randint(0, 3)
            for _ in range(daily_events):
                direction = rng.choices(["inflow", "outflow"], weights=[0.55, 0.45])[0]
                counterparty, category = rng.choice(_COUNTERPARTIES[direction])
                base = 1500 if direction == "inflow" else 900
                amount = round(base * rng.uniform(0.5, 6.0), 2)
                transactions.append(
                    {
                        "direction": direction,
                        "amount": amount,
                        "currency": currency,
                        "category": category,
                        "counterparty": counterparty,
                        "description": counterparty,
                        "occurred_at": occurred_at,
                    }
                )
        # One deliberate outlier so the anomaly rule and health score have
        # something real to catch, same as a genuine unusual transaction would.
        transactions.append(
            {
                "direction": "outflow",
                "amount": 48000.00,
                "currency": currency,
                "category": "uncategorized",
                "counterparty": "Unrecognized Transfer",
                "description": "Unrecognized Transfer",
                "occurred_at": now - timedelta(days=2),
            }
        )
        return transactions
