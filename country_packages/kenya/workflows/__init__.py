"""
Kenya Country Package - Workflow Extensions

Country-specific workflow metadata layered on top of the Kernel's
country-agnostic Workflow Engine (kernel/workflow_engine/engine.py).
Nothing here replaces a Kernel workflow - these are additional
triggers/notes the Workflow Engine may consult once a matching
capability exists.
"""

WORKFLOW_EXTENSIONS = [
    {
        "id": "kenya.large_cash_transaction_review",
        "trigger": "payment.received",
        "condition": "amount >= compliance.AML.large_cash_transaction_threshold_kes",
        "action": "flag_for_review",
    },
]
