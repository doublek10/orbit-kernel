"""Kenya Country Package - Compliance"""

KYC = {
    "individual_documents": ["national_id", "kra_pin"],
    "business_documents": ["certificate_of_incorporation", "cr12", "kra_pin_certificate", "business_permit"],
    "beneficial_ownership_threshold": 0.10,
}

AML = {
    "regulator": "Financial Reporting Centre (FRC)",
    "large_cash_transaction_threshold_kes": 1_000_000,
    "suspicious_activity_reporting": True,
}

BUSINESS_REGISTRATION = {
    "registrar": "Business Registration Service (BRS)",
    "identifiers": ["certificate_of_incorporation_number", "kra_pin"],
}

RECORD_RETENTION = {
    "financial_records_years": 7,
    "tax_records_years": 5,
}

GOVERNMENT_REPORTING = ["kra_itax_filing", "nssf_returns", "shif_returns", "housing_levy_returns"]

COMPLIANCE_RULES = [
    "Companies processing >= AML.large_cash_transaction_threshold_kes in a single transaction "
    "must be flagged for review before settlement.",
    "KYC documents must be verified before a provider connection goes live.",
]
