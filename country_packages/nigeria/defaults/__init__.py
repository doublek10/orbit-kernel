"""
Nigeria Country Package - Default Blueprint

Copied into a company's Blueprint at registration time. Keys match
exactly what kernel/company_blueprint/validator.py accepts, so this
dict can be handed straight to VersionManager.publish() without
transformation.
"""

DEFAULT_BLUEPRINT = {
    "business_type": "other",
    "priorities": ["cash_flow_visibility", "fraud_and_risk_alerts"],
    "large_transaction_threshold": 1_000_000.0,  # NGN
    "notify_on_large_transaction": True,
    "weekly_digest": True,
}

DEFAULT_PROVIDER = "mock_mobile_money"

RECOMMENDED_PROVIDERS = ["opay", "palmpay", "paystack"]

RECOMMENDED_INTEGRATIONS = ["quickbooks", "zoho_books"]
