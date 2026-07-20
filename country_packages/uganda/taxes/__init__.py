"""
Uganda Country Package - Taxes

Configuration only - the Rule Engine consumes these, nothing is
hardcoded in kernel/. Rates sourced from URA public guidance current at
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
    "zero_rated_examples": ["exports", "agricultural inputs", "medicine"],
    "exempt_examples": ["financial services", "education", "medical services"],
    "filing_frequency": "monthly",
    "filing_deadline_day": 15,
}

# PAYE bands (annual, UGX) - progressive. A further 10% surcharge
# applies to annual income above UGX 120,000,000 - modelled as its own
# top band here rather than a separate surcharge field.
PAYE_BANDS: list[TaxBand] = [
    TaxBand(lower=0, upper=2_820_000, rate=0.0),
    TaxBand(lower=2_820_000, upper=4_020_000, rate=0.10),
    TaxBand(lower=4_020_000, upper=4_920_000, rate=0.20),
    TaxBand(lower=4_920_000, upper=120_000_000, rate=0.30),
    TaxBand(lower=120_000_000, upper=None, rate=0.40),
]

CORPORATE_TAX = {
    "resident_rate": 0.30,
    "non_resident_rate": 0.30,
    "filing_frequency": "annual",
}

# URA's mobile money levy applies to withdrawals (and, historically,
# some transfers) rather than a digital-service tax on marketplaces.
MOBILE_MONEY_LEVY = {
    "withdrawal_rate": 0.005,
    "applies_to": "mobile money withdrawals",
}

WITHHOLDING_TAX = {
    "professional_fees_resident": 0.06,
    "professional_fees_non_resident": 0.15,
    "dividends_resident": 0.15,
    "interest_resident": 0.15,
}

PAYROLL_TAXES = {
    "nssf_employee_rate": 0.05,
    "nssf_employer_rate": 0.10,
    "local_service_tax_annual_max_ugx": 100_000,
}

GOVERNMENT_FILING = {
    "authority": "Uganda Revenue Authority (URA)",
    "portal": "URA e-Tax Portal",
    "paye_deadline_day": 15,
    "vat_deadline_day": 15,
}

TAX_REPORTS = ["vat_return", "paye_return", "corporate_tax_return", "withholding_tax_return", "mobile_money_levy_return"]
