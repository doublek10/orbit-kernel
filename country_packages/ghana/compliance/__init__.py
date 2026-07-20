"""Ghana Country Package - Compliance"""

KYC = {
    "individual_documents": ["ghana_card", "tin"],
    "business_documents": ["certificate_of_incorporation", "business_registration_certificate", "tin_certificate"],
    "beneficial_ownership_threshold": 0.10,
}

AML = {
    "regulator": "Financial Intelligence Centre (FIC)",
    "large_cash_transaction_threshold_ghs": 50_000,
    "suspicious_activity_reporting": True,
}

BUSINESS_REGISTRATION = {
    "registrar": "Office of the Registrar of Companies (ORC)",
    "identifiers": ["certificate_of_incorporation_number", "tin"],
}

RECORD_RETENTION = {
    "financial_records_years": 6,
    "tax_records_years": 6,
}

GOVERNMENT_REPORTING = ["gra_tax_filing", "ssnit_returns", "e_levy_returns"]

COMPLIANCE_RULES = [
    "Companies processing >= AML.large_cash_transaction_threshold_ghs in a single transaction "
    "must be flagged for review before settlement.",
    "KYC documents must be verified before a provider connection goes live.",
]
