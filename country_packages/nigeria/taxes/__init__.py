"""
Nigeria Country Package - Taxes

Configuration only - the Rule Engine consumes these, nothing is
hardcoded in kernel/. Rates sourced from FIRS public guidance current
at the time this package was authored; monitoring/ is what keeps this
from going stale, by proposing versioned updates rather than the
Kernel ever hardcoding a rate.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TaxBand:
    lower: float
    upper: float | None  # None = no upper bound
    rate: float  # fraction, e.g. 0.30 = 30%


VAT = {
    "standard_rate": 0.075,
    "zero_rated_examples": ["exports", "basic food items", "medical products"],
    "exempt_examples": ["financial services", "education", "medical services"],
    "filing_frequency": "monthly",
    "filing_deadline_day": 21,
}

# Personal income tax / PAYE bands (annual, NGN) - progressive.
PAYE_BANDS: list[TaxBand] = [
    TaxBand(lower=0, upper=300_000, rate=0.07),
    TaxBand(lower=300_000, upper=600_000, rate=0.11),
    TaxBand(lower=600_000, upper=1_100_000, rate=0.15),
    TaxBand(lower=1_100_000, upper=1_600_000, rate=0.19),
    TaxBand(lower=1_600_000, upper=3_200_000, rate=0.21),
    TaxBand(lower=3_200_000, upper=None, rate=0.24),
]

# Companies Income Tax (CIT) - tiered by annual turnover rather than a
# flat resident/non-resident split.
CORPORATE_TAX = {
    "small_company_turnover_max_ngn": 25_000_000,
    "small_company_rate": 0.0,
    "medium_company_turnover_max_ngn": 100_000_000,
    "medium_company_rate": 0.20,
    "large_company_rate": 0.30,
    "filing_frequency": "annual",
}

# Electronic Money Transfer Levy - a flat charge on qualifying
# electronic transfers, not a percentage-based digital service tax.
ELECTRONIC_MONEY_TRANSFER_LEVY = {
    "flat_amount_ngn": 50,
    "applies_to": "electronic transfers of NGN 10,000 or more received into a bank account",
    "exempt_threshold_ngn": 10_000,
}

WITHHOLDING_TAX = {
    "goods_and_services": 0.05,
    "professional_fees": 0.10,
    "dividends_resident": 0.10,
    "rent_resident": 0.10,
}

PAYROLL_TAXES = {
    "pension_employee_rate": 0.08,
    "pension_employer_rate": 0.10,
    "nhf_employee_rate": 0.025,  # National Housing Fund
    "nsitf_employer_rate": 0.01,  # Nigeria Social Insurance Trust Fund
}

GOVERNMENT_FILING = {
    "authority": "Federal Inland Revenue Service (FIRS)",
    "portal": "TaxPro-Max",
    "paye_deadline_day": 10,
    "vat_deadline_day": 21,
}

TAX_REPORTS = ["vat_return", "paye_return", "cit_return", "withholding_tax_return", "emtl_return"]
