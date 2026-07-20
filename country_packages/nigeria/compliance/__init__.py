"""Nigeria Country Package - Compliance"""

KYC = {
    "individual_documents": ["national_id_nin", "bvn", "tin"],
    "business_documents": ["cac_certificate", "cac_status_report", "tin_certificate"],
    "beneficial_ownership_threshold": 0.05,
}

AML = {
    "regulator": "Nigerian Financial Intelligence Unit (NFIU)",
    "large_cash_transaction_threshold_ngn": 5_000_000,
    "suspicious_activity_reporting": True,
}

BUSINESS_REGISTRATION = {
    "registrar": "Corporate Affairs Commission (CAC)",
    "identifiers": ["cac_registration_number", "tin"],
}

RECORD_RETENTION = {
    "financial_records_years": 6,
    "tax_records_years": 6,
}

GOVERNMENT_REPORTING = ["firs_taxpro_max_filing", "pencom_returns", "nsitf_returns"]

COMPLIANCE_RULES = [
    "Companies processing >= AML.large_cash_transaction_threshold_ngn in a single transaction "
    "must be flagged for review before settlement.",
    "KYC documents must be verified before a provider connection goes live.",
]
