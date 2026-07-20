"""
Tanzania Country Package - Workflow Extensions

Country-specific workflow metadata layered on top of the Kernel's
country-agnostic Workflow Engine.
"""

WORKFLOW_EXTENSIONS = [
    {
        "id": "tanzania.large_cash_transaction_review",
        "trigger": "payment.received",
        "condition": "amount >= compliance.AML.large_cash_transaction_threshold_tzs",
        "action": "flag_for_review",
    },
    {
        "id": "tanzania.mobile_money_levy",
        "trigger": "payment.mpesa.received",
        "condition": "amount > taxes.MOBILE_MONEY_LEVY.exempt_threshold_tzs",
        "action": "apply_mobile_money_levy",
    },
]
