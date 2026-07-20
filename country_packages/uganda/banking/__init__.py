"""Uganda Country Package - Banking"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BankDefinition:
    code: str  # Uganda Bankers' Association clearing code
    swift_code: str
    name: str
    supports_rtgs: bool
    supports_eft: bool
    supports_instant: bool  # Uganda National Interbank Settlement instant rail


SUPPORTED_BANKS: list[BankDefinition] = [
    BankDefinition(code="040", swift_code="SBICUGKX", name="Stanbic Bank Uganda", supports_rtgs=True, supports_eft=True, supports_instant=True),
    BankDefinition(code="060", swift_code="CERBUGKA", name="Centenary Bank", supports_rtgs=True, supports_eft=True, supports_instant=True),
    BankDefinition(code="010", swift_code="BARCUGKX", name="Absa Bank Uganda", supports_rtgs=True, supports_eft=True, supports_instant=True),
    BankDefinition(code="030", swift_code="SCBLUGKA", name="Standard Chartered Uganda", supports_rtgs=True, supports_eft=True, supports_instant=False),
    BankDefinition(code="050", swift_code="EQBLUGKA", name="Equity Bank Uganda", supports_rtgs=True, supports_eft=True, supports_instant=True),
]

TRANSFER_TYPES = ["rtgs", "eft", "instant", "internal"]

SETTLEMENT_RULES = {
    "rtgs": {"same_day_cutoff": "15:00", "timezone": "Africa/Kampala", "settlement": "same_day"},
    "eft": {"same_day_cutoff": None, "timezone": "Africa/Kampala", "settlement": "next_business_day"},
    "instant": {"same_day_cutoff": None, "timezone": "Africa/Kampala", "settlement": "instant"},
}

# Ugandan bank account numbers are typically 10-14 digits.
ACCOUNT_REFERENCE_FORMAT = r"^\d{10,14}$"

_BY_CODE = {b.code: b for b in SUPPORTED_BANKS}


def get_bank(code: str) -> BankDefinition | None:
    return _BY_CODE.get(code)
