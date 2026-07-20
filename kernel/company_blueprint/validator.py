"""
Blueprint Validator

Rejects malformed Blueprint input before it touches Postgres or an
active company's live configuration. Deliberately conservative: an
invalid Blueprint fails loudly at publish time (a 4xx back through the
Gateway), not silently, and never partially - either the whole payload
is valid or nothing is written.

This is intentionally *not* JSON-schema-generic (see Schema Engine for
that, which validates incoming *event* payloads against a company's own
declared schemas). This validator only knows the fixed shape of the
Blueprint itself.
"""

VALID_BUSINESS_TYPES = {
    "retail",
    "services",
    "agriculture",
    "manufacturing",
    "technology",
    "other",
}

VALID_PRIORITIES = {
    "cash_flow_visibility",
    "expense_control",
    "payroll_accuracy",
    "fraud_and_risk_alerts",
    "growth_forecasting",
}

# Matches Finding.kind values in kernel/intelligence_engine/models.py -
# these are the only capabilities the Intelligence Engine has today, so
# they're the only ones a Blueprint can govern. An empty list rejects
# outright rather than silently meaning "everything off" - use the
# absent/default case (all capabilities) if that's what's intended.
VALID_CAPABILITIES = {"health", "trend", "spend", "anomaly", "forecast"}


class BlueprintValidationError(ValueError):
    """Raised for any structurally or semantically invalid Blueprint payload."""


def validate_blueprint_input(payload: dict) -> dict:
    business_type = (payload.get("business_type") or "").strip()
    if business_type not in VALID_BUSINESS_TYPES:
        raise BlueprintValidationError(
            f"business_type must be one of {sorted(VALID_BUSINESS_TYPES)}"
        )

    priorities = payload.get("priorities") or []
    if not isinstance(priorities, list) or not all(isinstance(p, str) for p in priorities):
        raise BlueprintValidationError("priorities must be a list of strings")
    unknown = sorted(set(priorities) - VALID_PRIORITIES)
    if unknown:
        raise BlueprintValidationError(f"unknown priorities: {unknown}")

    threshold_raw = payload.get("large_transaction_threshold")
    threshold: float | None = None
    if threshold_raw not in (None, ""):
        try:
            threshold = float(threshold_raw)
        except (TypeError, ValueError):
            raise BlueprintValidationError("large_transaction_threshold must be numeric")
        if threshold < 0:
            raise BlueprintValidationError("large_transaction_threshold cannot be negative")

    capabilities_raw = payload.get("enabled_capabilities")
    if capabilities_raw is None:
        capabilities = sorted(VALID_CAPABILITIES)
    else:
        if not isinstance(capabilities_raw, list) or not all(isinstance(c, str) for c in capabilities_raw):
            raise BlueprintValidationError("enabled_capabilities must be a list of strings")
        if not capabilities_raw:
            raise BlueprintValidationError(
                "enabled_capabilities cannot be an empty list - omit the field to enable all capabilities"
            )
        unknown_capabilities = sorted(set(capabilities_raw) - VALID_CAPABILITIES)
        if unknown_capabilities:
            raise BlueprintValidationError(f"unknown enabled_capabilities: {unknown_capabilities}")
        capabilities = capabilities_raw

    categories_raw = payload.get("allowed_categories")
    categories: list[str] | None = None
    if categories_raw not in (None, ""):
        if not isinstance(categories_raw, list) or not all(isinstance(c, str) and c.strip() for c in categories_raw):
            raise BlueprintValidationError("allowed_categories must be a list of non-empty strings, or null for unrestricted")
        categories = [c.strip() for c in categories_raw]
        if not categories:
            categories = None

    return {
        "business_type": business_type,
        "priorities": priorities,
        "large_transaction_threshold": threshold,
        "notify_on_large_transaction": bool(payload.get("notify_on_large_transaction", True)),
        "weekly_digest": bool(payload.get("weekly_digest", True)),
        "enabled_capabilities": capabilities,
        "allowed_categories": categories,
    }
