"""
Nigeria Country Package - Workflow Extensions

Country-specific workflow metadata layered on top of the Kernel's
country-agnostic Workflow Engine.
"""

WORKFLOW_EXTENSIONS = [
    {
        "id": "nigeria.large_cash_transaction_review",
        "trigger": "payment.received",
        "condition": "amount >= compliance.AML.large_cash_transaction_threshold_ngn",
        "action": "flag_for_review",
    },
    {
        "id": "nigeria.electronic_money_transfer_levy",
        "trigger": "payment.bank.completed",
        "condition": "amount >= taxes.ELECTRONIC_MONEY_TRANSFER_LEVY.exempt_threshold_ngn",
        "action": "apply_emtl",
    },
]
