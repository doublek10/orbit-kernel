"""
Kenya Country Package - Event Definitions

Country events this package can emit, each with the schema shape the
Schema Engine expects (required/optional fields), a version, and which
providers can produce it. The Workflow Engine and Schema Engine consume
this to validate incoming provider payloads once they've passed through
mappings/.
"""

EVENTS: dict[str, dict] = {
    "payment.received": {
        "version": 1,
        "required_fields": ["amount", "currency", "reference"],
        "optional_fields": ["payer", "memo"],
        "supported_providers": ["mock_mobile_money"],
    },
    "payment.mpesa.received": {
        "version": 1,
        "required_fields": ["amount", "mpesa_receipt_number", "phone_number", "transaction_date"],
        "optional_fields": ["account_reference"],
        "supported_providers": ["mpesa"],
    },
    "payment.mpesa.failed": {
        "version": 1,
        "required_fields": ["result_code", "result_desc"],
        "optional_fields": [],
        "supported_providers": ["mpesa"],
    },
    "payment.bank.completed": {
        "version": 1,
        "required_fields": ["amount", "bank_code", "reference"],
        "optional_fields": ["narrative"],
        "supported_providers": ["kcb_bank", "equity_bank"],
    },
    "invoice.created": {
        "version": 1,
        "required_fields": ["invoice_id", "amount", "currency", "due_date"],
        "optional_fields": ["customer_id"],
        "supported_providers": [],
    },
    "invoice.paid": {
        "version": 1,
        "required_fields": ["invoice_id", "amount", "paid_at"],
        "optional_fields": [],
        "supported_providers": [],
    },
    "tax.filed": {
        "version": 1,
        "required_fields": ["tax_type", "period", "amount"],
        "optional_fields": ["reference_number"],
        "supported_providers": [],
    },
}
