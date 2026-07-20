"""
Rule Engine

Business rules live here, and only here - never inside providers, never
inside the Workflow Engine. Two rule sets are implemented for the
financial core:

- "transaction.categorize": guesses a spend/income category from a free
  text description, using simple keyword matching. Good enough to make
  the ledger and dashboard useful today; swap for a trained classifier
  later without touching any caller.
- "transaction.anomaly": flags a transaction as unusual relative to the
  account's recent history, so the Financial Graph and dashboard can
  surface it without every caller re-implementing the heuristic.
"""

from dataclasses import dataclass

_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "revenue": ("payment received", "invoice", "sale", "customer", "till"),
    "salary": ("salary", "payroll", "wages"),
    "supplier": ("supplier", "wholesale", "restock", "inventory"),
    "rent": ("rent", "lease"),
    "utilities": ("electricity", "kplc", "water", "internet", "airtime", "data bundle"),
    "transport": ("fuel", "uber", "bolt", "matatu", "transport"),
    "transfer": ("mpesa", "m-pesa", "mobile money", "transfer", "till"),
    "tax": ("kra", "tax", "vat", "levy"),
}


@dataclass(frozen=True)
class RuleResult:
    outcome: str
    details: dict


class RuleEngine:
    async def evaluate(self, ctx, rule_set: str, payload: dict | None = None) -> RuleResult:
        payload = payload or {}
        if rule_set == "transaction.categorize":
            return RuleResult("categorized", {"category": self._categorize(payload.get("description", ""))})
        if rule_set == "transaction.anomaly":
            return RuleResult("evaluated", {"is_anomaly": self._is_anomaly(payload)})
        raise NotImplementedError(f"Rule set '{rule_set}' not implemented yet")

    def _categorize(self, description: str) -> str:
        text = description.lower()
        for category, keywords in _CATEGORY_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                return category
        return "uncategorized"

    def _is_anomaly(self, payload: dict) -> bool:
        amount = float(payload.get("amount", 0))
        recent_average = float(payload.get("recent_average", 0))
        if recent_average <= 0:
            return False
        # More than 3x the recent average outflow is flagged for review -
        # a simple, explainable rule rather than a black-box model.
        return amount > recent_average * 3
