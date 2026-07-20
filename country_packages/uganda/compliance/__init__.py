"""Uganda Country Package - Compliance"""

KYC = {
    "individual_documents": ["national_id_nin", "tin"],
    "business_documents": ["certificate_of_incorporation", "trading_license", "tin_certificate"],
    "beneficial_ownership_threshold": 0.10,
}

AML = {
    "regulator": "Financial Intelligence Authority (FIA)",
    "large_cash_transaction_threshold_ugx": 20_000_000,
    "suspicious_activity_reporting": True,
}

BUSINESS_REGISTRATION = {
    "registrar": "Uganda Registration Services Bureau (URSB)",
    "identifiers": ["certificate_of_incorporation_number", "tin"],
}

RECORD_RETENTION = {
    "financial_records_years": 6,
    "tax_records_years": 5,
}

GOVERNMENT_REPORTING = ["ura_etax_filing", "nssf_returns", "local_service_tax_returns"]

COMPLIANCE_RULES = [
    "Companies processing >= AML.large_cash_transaction_threshold_ugx in a single transaction "
    "must be flagged for review before settlement.",
    "KYC documents must be verified before a provider connection goes live.",
]
