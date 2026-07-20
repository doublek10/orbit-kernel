"""Tanzania Country Package - Compliance"""

KYC = {
    "individual_documents": ["national_id_nida", "tin"],
    "business_documents": ["certificate_of_incorporation", "business_license", "tin_certificate"],
    "beneficial_ownership_threshold": 0.10,
}

AML = {
    "regulator": "Financial Intelligence Unit (FIU)",
    "large_cash_transaction_threshold_tzs": 20_000_000,
    "suspicious_activity_reporting": True,
}

BUSINESS_REGISTRATION = {
    "registrar": "Business Registrations and Licensing Agency (BRELA)",
    "identifiers": ["certificate_of_incorporation_number", "tin"],
}

RECORD_RETENTION = {
    "financial_records_years": 5,
    "tax_records_years": 5,
}

GOVERNMENT_REPORTING = ["tra_efiling", "nssf_returns", "sdl_returns"]

COMPLIANCE_RULES = [
    "Companies processing >= AML.large_cash_transaction_threshold_tzs in a single transaction "
    "must be flagged for review before settlement.",
    "KYC documents must be verified before a provider connection goes live.",
]
