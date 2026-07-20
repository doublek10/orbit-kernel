"""
Nigeria Country Package - Event Definitions

Same shape as Kenya's, Ghana's, Uganda's and Tanzania's events modules.
"""

EVENTS: dict[str, dict] = {
    "payment.received": {
        "version": 1,
        "required_fields": ["amount", "currency", "reference"],
        "optional_fields": ["payer", "memo"],
        "supported_providers": ["mock_mobile_money"],
    },
    "payment.opay.received": {
        "version": 1,
        "required_fields": ["amount", "reference", "customer_msisdn"],
        "optional_fields": ["order_id"],
        "supported_providers": ["opay"],
    },
    "payment.opay.failed": {
        "version": 1,
        "required_fields": ["status", "reason"],
        "optional_fields": [],
        "supported_providers": ["opay"],
    },
    "payment.palmpay.received": {
        "version": 1,
        "required_fields": ["amount", "order_no", "customer_number"],
        "optional_fields": [],
        "supported_providers": ["palmpay"],
    },
    "payment.paga.received": {
        "version": 1,
        "required_fields": ["amount", "reference_number", "payer"],
        "optional_fields": [],
        "supported_providers": ["paga"],
    },
    "payment.bank.completed": {
        "version": 1,
        "required_fields": ["amount", "bank_code", "reference"],
        "optional_fields": ["narrative"],
        "supported_providers": ["gtbank", "access_bank", "zenith_bank"],
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
