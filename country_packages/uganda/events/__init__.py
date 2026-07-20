"""
Uganda Country Package - Event Definitions

Same shape as Kenya's and Ghana's events modules.
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
        "supported_providers": ["mtn_momo_ug"],
    },
    "payment.mtn_momo.failed": {
        "version": 1,
        "required_fields": ["status", "reason"],
        "optional_fields": [],
        "supported_providers": ["mtn_momo_ug"],
    },
    "payment.airtel.received": {
        "version": 1,
        "required_fields": ["amount", "reference", "msisdn"],
        "optional_fields": [],
        "supported_providers": ["airtel_money_ug"],
    },
    "payment.airtel.failed": {
        "version": 1,
        "required_fields": ["status_code", "reason"],
        "optional_fields": [],
        "supported_providers": ["airtel_money_ug"],
    },
    "payment.bank.completed": {
        "version": 1,
        "required_fields": ["amount", "bank_code", "reference"],
        "optional_fields": ["narrative"],
        "supported_providers": ["stanbic_bank_ug", "centenary_bank"],
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
