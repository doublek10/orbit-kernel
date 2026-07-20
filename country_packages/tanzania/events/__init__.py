"""
Tanzania Country Package - Event Definitions

Same shape as Kenya's, Ghana's and Uganda's events modules.
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
        "supported_providers": ["mpesa_tz"],
    },
    "payment.mpesa.failed": {
        "version": 1,
        "required_fields": ["result_code", "result_desc"],
        "optional_fields": [],
        "supported_providers": ["mpesa_tz"],
    },
    "payment.tigo_pesa.received": {
        "version": 1,
        "required_fields": ["amount", "reference", "msisdn"],
        "optional_fields": [],
        "supported_providers": ["tigo_pesa"],
    },
    "payment.tigo_pesa.failed": {
        "version": 1,
        "required_fields": ["status_code", "reason"],
        "optional_fields": [],
        "supported_providers": ["tigo_pesa"],
    },
    "payment.halopesa.received": {
        "version": 1,
        "required_fields": ["amount", "reference", "msisdn"],
        "optional_fields": [],
        "supported_providers": ["halopesa"],
    },
    "payment.bank.completed": {
        "version": 1,
        "required_fields": ["amount", "bank_code", "reference"],
        "optional_fields": ["narrative"],
        "supported_providers": ["crdb_bank", "nmb_bank"],
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
