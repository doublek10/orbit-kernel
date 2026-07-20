"""
Kenya Country Package - Taxes

Configuration only, per the spec ("No tax calculations are hardcoded" -
the Rule Engine consumes these definitions). Rates sourced from KRA
public guidance current at the time this package was authored; the
Regulatory Intelligence service (monitoring/) is what keeps this from
going stale, by proposing versioned updates rather than the Kernel ever
hardcoding a rate.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TaxBand:
    lower: float
    upper: float | None  # None = no upper bound
    rate: float  # fraction, e.g. 0.30 = 30%


VAT = {
    "standard_rate": 0.16,
    "zero_rated_examples": ["exports", "medicine", "agricultural inputs"],
    "exempt_examples": ["financial services", "education", "medical services"],
    "filing_frequency": "monthly",
    "filing_deadline_day": 20,
}

# PAYE bands (annual, KES) - progressive.
PAYE_BANDS: list[TaxBand] = [
    TaxBand(lower=0, upper=288_000, rate=0.10),
    TaxBand(lower=288_000, upper=388_000, rate=0.25),
    TaxBand(lower=388_000, upper=6_000_000, rate=0.30),
    TaxBand(lower=6_000_000, upper=9_600_000, rate=0.325),
    TaxBand(lower=9_600_000, upper=None, rate=0.35),
]

CORPORATE_TAX = {
    "resident_rate": 0.30,
    "non_resident_rate": 0.375,
    "filing_frequency": "annual",
}

DIGITAL_SERVICE_TAX = {
    "rate": 0.015,
    "applies_to": "income from services provided through a digital marketplace",
}

WITHHOLDING_TAX = {
    "professional_fees_resident": 0.05,
    "professional_fees_non_resident": 0.20,
    "dividends_resident": 0.05,
    "interest_resident": 0.15,
}

PAYROLL_TAXES = {
    "nssf_employee_rate": 0.06,
    "nssf_employer_rate": 0.06,
    "shif_rate": 0.0275,  # Social Health Insurance Fund
    "housing_levy_employee_rate": 0.015,
    "housing_levy_employer_rate": 0.015,
}

GOVERNMENT_FILING = {
    "authority": "Kenya Revenue Authority (KRA)",
    "portal": "iTax",
    "paye_deadline_day": 9,
    "vat_deadline_day": 20,
}

TAX_REPORTS = ["vat_return", "paye_return", "corporate_tax_return", "withholding_tax_return"]
