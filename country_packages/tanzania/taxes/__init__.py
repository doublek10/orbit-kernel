"""
Tanzania Country Package - Taxes

Configuration only - the Rule Engine consumes these, nothing is
hardcoded in kernel/. Rates sourced from TRA public guidance current at
the time this package was authored; monitoring/ is what keeps this from
going stale, by proposing versioned updates rather than the Kernel ever
hardcoding a rate.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TaxBand:
    lower: float
    upper: float | None  # None = no upper bound
    rate: float  # fraction, e.g. 0.30 = 30%


VAT = {
    "standard_rate": 0.18,
    "zero_rated_examples": ["exports", "agricultural inputs"],
    "exempt_examples": ["financial services", "education", "medical services"],
    "filing_frequency": "monthly",
    "filing_deadline_day": 20,
}

# PAYE bands (annual, TZS) - progressive.
PAYE_BANDS: list[TaxBand] = [
    TaxBand(lower=0, upper=3_240_000, rate=0.0),
    TaxBand(lower=3_240_000, upper=6_240_000, rate=0.08),
    TaxBand(lower=6_240_000, upper=9_120_000, rate=0.20),
    TaxBand(lower=9_120_000, upper=12_000_000, rate=0.25),
    TaxBand(lower=12_000_000, upper=None, rate=0.30),
]

CORPORATE_TAX = {
    "resident_rate": 0.30,
    "non_resident_rate": 0.30,
    "filing_frequency": "annual",
}

# TRA's mobile money transaction levy - tiered by transaction band
# rather than a flat rate; kept as a simple representative band here,
# with the caveat that the real schedule has more tiers than this.
MOBILE_MONEY_LEVY = {
    "applies_to": "mobile money withdrawals and transfers above the exempt threshold",
    "exempt_threshold_tzs": 1_000,
    "representative_rate": 0.007,
}

WITHHOLDING_TAX = {
    "professional_fees_resident": 0.05,
    "professional_fees_non_resident": 0.15,
    "dividends_resident": 0.10,
    "interest_resident": 0.10,
}

PAYROLL_TAXES = {
    "nssf_employee_rate": 0.10,
    "nssf_employer_rate": 0.10,
    "sdl_employer_rate": 0.035,  # Skills Development Levy
}

GOVERNMENT_FILING = {
    "authority": "Tanzania Revenue Authority (TRA)",
    "portal": "TRA e-Filing (TAWA / Online Portal)",
    "paye_deadline_day": 7,
    "vat_deadline_day": 20,
}

TAX_REPORTS = ["vat_return", "paye_return", "corporate_tax_return", "withholding_tax_return", "sdl_return"]
