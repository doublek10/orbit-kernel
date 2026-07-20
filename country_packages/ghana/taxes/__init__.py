"""
Ghana Country Package - Taxes

Configuration only - the Rule Engine consumes these, nothing is
hardcoded in kernel/. Rates sourced from GRA public guidance current at
the time this package was authored; monitoring/ is what keeps this from
going stale, by proposing versioned updates rather than the Kernel ever
hardcoding a rate.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TaxBand:
    lower: float
    upper: float | None  # None = no upper bound
    rate: float  # fraction, e.g. 0.25 = 25%


# Standard VAT plus the flat "straight-line" levies GRA applies
# alongside it (NHIL, GETFund, COVID-19 Health Recovery Levy) - kept
# separate here since they're calculated independently, not compounded.
VAT = {
    "standard_rate": 0.15,
    "nhil_rate": 0.025,  # National Health Insurance Levy
    "getfund_rate": 0.025,  # Ghana Education Trust Fund Levy
    "covid_levy_rate": 0.01,
    "zero_rated_examples": ["exports", "agricultural inputs"],
    "exempt_examples": ["financial services", "education", "medical services"],
    "filing_frequency": "monthly",
    "filing_deadline_day": 30,
}

# PAYE bands (annual, GHS) - progressive.
PAYE_BANDS: list[TaxBand] = [
    TaxBand(lower=0, upper=4_824, rate=0.0),
    TaxBand(lower=4_824, upper=6_144, rate=0.05),
    TaxBand(lower=6_144, upper=7_944, rate=0.10),
    TaxBand(lower=7_944, upper=44_544, rate=0.175),
    TaxBand(lower=44_544, upper=240_144, rate=0.25),
    TaxBand(lower=240_144, upper=None, rate=0.30),
]

CORPORATE_TAX = {
    "resident_rate": 0.25,
    "non_resident_rate": 0.25,
    "filing_frequency": "annual",
}

# Ghana taxes electronic transfers (including mobile money) directly,
# rather than a digital-service tax on marketplaces the way Kenya does.
ELECTRONIC_TRANSFER_LEVY = {
    "rate": 0.01,
    "applies_to": "electronic transfers above the exempt threshold, including mobile money",
    "exempt_threshold_ghs": 100,
}

WITHHOLDING_TAX = {
    "professional_fees_resident": 0.075,
    "professional_fees_non_resident": 0.20,
    "dividends_resident": 0.08,
    "interest_resident": 0.08,
}

PAYROLL_TAXES = {
    "ssnit_employee_rate": 0.055,
    "ssnit_employer_rate": 0.13,
    "tier2_employer_rate": 0.05,  # included within the 13% employer contribution
}

GOVERNMENT_FILING = {
    "authority": "Ghana Revenue Authority (GRA)",
    "portal": "Taxpayers Portal / GRA Digital Platform",
    "paye_deadline_day": 15,
    "vat_deadline_day": 30,
}

TAX_REPORTS = ["vat_return", "paye_return", "corporate_tax_return", "withholding_tax_return", "e_levy_return"]
