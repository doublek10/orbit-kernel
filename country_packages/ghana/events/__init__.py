"""
Ghana Country Package - Event Definitions

Same shape as Kenya's events module - required/optional fields, a
version, and which providers can produce each event.
"""

EVENTS: dict[str, dict] = {
    "payment.received": {
        "version": 1,
        "required_fields": ["amount", "currency", "reference"],
        "optional_fields": ["payer", "memo"],
        "supported_providers": ["mock_mobile_money"],
    },
    "payment.mtn_momo.received": {
        "version": 1,
        "required_fields": ["amount", "financial_transaction_id", "payer_msisdn"],
        "optional_fields": ["external_id"],
        "supported_providers": ["mtn_momo_gh"],
    },
    "payment.mtn_momo.failed": {
        "version": 1,
        "required_fields": ["status", "reason"],
        "optional_fields": [],
        "supported_providers": ["mtn_momo_gh"],
    },
    "payment.vodafone_cash.received": {
        "version": 1,
        "required_fields": ["amount", "transaction_id", "msisdn"],
        "optional_fields": ["reference"],
        "supported_providers": ["vodafone_cash"],
    },
    "payment.bank.completed": {
        "version": 1,
        "required_fields": ["amount", "bank_code", "reference"],
        "optional_fields": ["narrative"],
        "supported_providers": ["gcb_bank", "ecobank_gh"],
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
