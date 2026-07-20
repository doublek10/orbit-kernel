"""
Blueprint-Driven Recommendations

Design Principle #8: "Every workflow uses the active Blueprint." This
module is the one place that translates a company's Blueprint
(business_type, priorities) into concrete adjustments elsewhere in the
product - which marketplace apps get a "Recommended" badge, which
Financial Connections / Business Systems catalog entries surface as
recommended, and which AI insights get bumped to the top when a company
hasn't published a Blueprint yet (or picked a business type / priority
this module doesn't have a mapping for), every lookup here returns an
empty set - nothing is hidden or reordered, the rest of the product
falls back to its unpersonalized default.
"""

PRIORITY_INSIGHT_IDS: dict[str, set[str]] = {
    "cash_flow_visibility": {"flow-trend", "forecast-30d"},
    "expense_control": {"top-category"},
    "fraud_and_risk_alerts": {"anomalies"},
    "growth_forecasting": {"forecast-30d"},
    "payroll_accuracy": set(),
}

PRIORITY_APP_CATEGORIES: dict[str, set[str]] = {
    "cash_flow_visibility": {"reporting"},
    "expense_control": {"reporting", "automation"},
    "fraud_and_risk_alerts": {"intelligence"},
    "growth_forecasting": {"intelligence"},
    "payroll_accuracy": {"automation"},
}

BUSINESS_TYPE_FINANCIAL_CATEGORIES: dict[str, set[str]] = {
    "retail": {"payment_gateway", "mobile_money"},
    "services": {"bank", "payment_gateway"},
    "agriculture": {"mobile_money", "bank"},
    "manufacturing": {"bank", "payment_gateway"},
    "technology": {"payment_gateway", "crypto"},
    "other": set(),
}

BUSINESS_TYPE_SYSTEM_TYPES: dict[str, set[str]] = {
    "retail": {"pos", "inventory", "accounting"},
    "services": {"accounting", "crm"},
    "agriculture": {"inventory", "warehouse", "accounting"},
    "manufacturing": {"erp", "inventory", "warehouse"},
    "technology": {"crm", "accounting", "erp"},
    "other": set(),
}


def relevant_insight_ids(priorities: list[str]) -> set[str]:
    ids: set[str] = set()
    for p in priorities:
        ids |= PRIORITY_INSIGHT_IDS.get(p, set())
    return ids


def relevant_app_categories(priorities: list[str]) -> set[str]:
    categories: set[str] = set()
    for p in priorities:
        categories |= PRIORITY_APP_CATEGORIES.get(p, set())
    return categories


def recommended_financial_categories(business_type: str | None) -> set[str]:
    return BUSINESS_TYPE_FINANCIAL_CATEGORIES.get(business_type or "", set())


def recommended_system_types(business_type: str | None) -> set[str]:
    return BUSINESS_TYPE_SYSTEM_TYPES.get(business_type or "", set())
