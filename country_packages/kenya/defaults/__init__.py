"""
Kenya Country Package - Default Blueprint

Copied into a company's Blueprint at registration time (spec:
"Registration Flow" -> "Load Country Defaults" -> "Generate Initial
Company Blueprint"). Keys here match exactly what
kernel/company_blueprint/validator.py accepts, so this dict can be
handed straight to VersionManager.publish() without transformation.

business_type defaults to "other" deliberately - we don't know what the
company does yet at signup, and validator.py requires a valid value.
The Company Owner can immediately publish a more specific Blueprint
from the dashboard; this default only exists so the company is never
left without one.
"""

DEFAULT_BLUEPRINT = {
    "business_type": "other",
    "priorities": ["cash_flow_visibility", "fraud_and_risk_alerts"],
    "large_transaction_threshold": 100_000.0,  # KES
    "notify_on_large_transaction": True,
    "weekly_digest": True,
}

DEFAULT_PROVIDER = "mock_mobile_money"

RECOMMENDED_PROVIDERS = ["mpesa", "airtel_money", "flutterwave"]

RECOMMENDED_INTEGRATIONS = ["quickbooks", "zoho_books"]
