"""
Ghana Country Package - Workflow Extensions

Country-specific workflow metadata layered on top of the Kernel's
country-agnostic Workflow Engine.
"""

WORKFLOW_EXTENSIONS = [
    {
        "id": "ghana.large_cash_transaction_review",
        "trigger": "payment.received",
        "condition": "amount >= compliance.AML.large_cash_transaction_threshold_ghs",
        "action": "flag_for_review",
    },
    {
        "id": "ghana.electronic_transfer_levy",
        "trigger": "payment.received",
        "condition": "amount > taxes.ELECTRONIC_TRANSFER_LEVY.exempt_threshold_ghs",
        "action": "apply_e_levy",
    },
]
