"""
Uganda Country Package - Workflow Extensions

Country-specific workflow metadata layered on top of the Kernel's
country-agnostic Workflow Engine.
"""

WORKFLOW_EXTENSIONS = [
    {
        "id": "uganda.large_cash_transaction_review",
        "trigger": "payment.received",
        "condition": "amount >= compliance.AML.large_cash_transaction_threshold_ugx",
        "action": "flag_for_review",
    },
    {
        "id": "uganda.mobile_money_withdrawal_levy",
        "trigger": "payment.mtn_momo.received",
        "condition": "operation == 'withdrawal'",
        "action": "apply_mobile_money_levy",
    },
]
