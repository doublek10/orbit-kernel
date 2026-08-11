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
    "logistics_transportation": {"bank", "payment_gateway"},
    "construction_real_estate": {"bank"},
    "hospitality_tourism": {"payment_gateway", "mobile_money"},
    "healthcare": {"bank", "payment_gateway"},
    "education": {"bank", "payment_gateway"},
    "financial_services": {"bank", "payment_gateway", "crypto"},
    "insurance": {"bank", "payment_gateway"},
    "wholesale_distribution": {"bank", "payment_gateway"},
    "energy_utilities": {"bank"},
    "telecommunications": {"bank", "payment_gateway", "mobile_money"},
    "automotive": {"bank", "payment_gateway"},
    "pharmaceuticals": {"bank", "payment_gateway"},
    "media_entertainment": {"payment_gateway", "crypto"},
    "nonprofits_ngos": {"bank", "mobile_money"},
    "government_public_sector": {"bank"},
    "mining_natural_resources": {"bank"},
    "import_export_trading": {"bank", "payment_gateway"},
    "property_management": {"bank", "mobile_money"},
    "food_processing_agribusiness": {"mobile_money", "bank"},
    "security_services": {"bank", "mobile_money"},
    "cleaning_facility_management": {"bank", "mobile_money"},
    "recruitment_hr": {"bank", "payment_gateway"},
    "travel_aviation": {"payment_gateway", "bank"},
    "fisheries_aquaculture": {"mobile_money", "bank"},
    "professional_associations": {"bank", "payment_gateway"},
    "other": set(),
}

BUSINESS_TYPE_SYSTEM_TYPES: dict[str, set[str]] = {
    "retail": {"pos", "inventory", "accounting"},
    "services": {"accounting", "crm"},
    "agriculture": {"inventory", "warehouse", "accounting"},
    "manufacturing": {"erp", "inventory", "warehouse"},
    "technology": {"crm", "accounting", "erp"},
    "logistics_transportation": {"inventory", "warehouse", "accounting"},
    "construction_real_estate": {"accounting", "erp"},
    "hospitality_tourism": {"pos", "accounting"},
    "healthcare": {"accounting", "crm"},
    "education": {"accounting", "crm"},
    "financial_services": {"accounting", "erp"},
    "insurance": {"accounting", "crm"},
    "wholesale_distribution": {"inventory", "warehouse", "erp"},
    "energy_utilities": {"erp", "accounting"},
    "telecommunications": {"crm", "erp"},
    "automotive": {"inventory", "pos", "erp"},
    "pharmaceuticals": {"inventory", "warehouse", "erp"},
    "media_entertainment": {"crm", "accounting"},
    "nonprofits_ngos": {"accounting", "crm"},
    "government_public_sector": {"accounting", "erp"},
    "mining_natural_resources": {"inventory", "warehouse", "erp"},
    "import_export_trading": {"inventory", "warehouse", "erp"},
    "property_management": {"accounting", "crm"},
    "food_processing_agribusiness": {"inventory", "warehouse", "accounting"},
    "security_services": {"hr", "accounting"},
    "cleaning_facility_management": {"hr", "accounting"},
    "recruitment_hr": {"hr", "crm"},
    "travel_aviation": {"crm", "accounting"},
    "fisheries_aquaculture": {"inventory", "warehouse", "accounting"},
    "professional_associations": {"crm", "accounting"},
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
