"""Ghana Country Package - Banking"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BankDefinition:
    code: str  # Ghana Interbank Settlement (GIS) sort code
    swift_code: str
    name: str
    supports_rtgs: bool
    supports_ach: bool
    supports_gip: bool  # GhIPSS Instant Pay


SUPPORTED_BANKS: list[BankDefinition] = [
    BankDefinition(code="040100", swift_code="GHCBGHAC", name="GCB Bank", supports_rtgs=True, supports_ach=True, supports_gip=True),
    BankDefinition(code="130100", swift_code="ECOCGHAC", name="Ecobank Ghana", supports_rtgs=True, supports_ach=True, supports_gip=True),
    BankDefinition(code="300100", swift_code="SCBLGHAC", name="Standard Chartered Ghana", supports_rtgs=True, supports_ach=True, supports_gip=False),
    BankDefinition(code="080100", swift_code="ABNGGHAC", name="Absa Bank Ghana", supports_rtgs=True, supports_ach=True, supports_gip=True),
    BankDefinition(code="200100", swift_code="ZENIGHAC", name="Zenith Bank Ghana", supports_rtgs=True, supports_ach=True, supports_gip=True),
]

TRANSFER_TYPES = ["rtgs", "ach", "gip", "internal"]

# GhIPSS Instant Pay (GIP) settles instantly; RTGS/ACH follow the same
# cutoff shape as Kenya's - consumed by the Workflow Engine, never
# hardcoded there.
SETTLEMENT_RULES = {
    "rtgs": {"same_day_cutoff": "15:00", "timezone": "Africa/Accra", "settlement": "same_day"},
    "ach": {"same_day_cutoff": None, "timezone": "Africa/Accra", "settlement": "next_business_day"},
    "gip": {"same_day_cutoff": None, "timezone": "Africa/Accra", "settlement": "instant"},
}

# Ghanaian bank account numbers are typically 10-16 digits.
ACCOUNT_REFERENCE_FORMAT = r"^\d{10,16}$"

_BY_CODE = {b.code: b for b in SUPPORTED_BANKS}


def get_bank(code: str) -> BankDefinition | None:
    return _BY_CODE.get(code)
