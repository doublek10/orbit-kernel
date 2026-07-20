"""Tanzania Country Package - Banking"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BankDefinition:
    code: str  # Tanzania Bankers Association clearing code
    swift_code: str
    name: str
    supports_rtgs: bool
    supports_eft: bool
    supports_tips: bool  # Tanzania Instant Payment System


SUPPORTED_BANKS: list[BankDefinition] = [
    BankDefinition(code="050", swift_code="CORUTZTZ", name="CRDB Bank", supports_rtgs=True, supports_eft=True, supports_tips=True),
    BankDefinition(code="040", swift_code="NMIBTZTZ", name="NMB Bank", supports_rtgs=True, supports_eft=True, supports_tips=True),
    BankDefinition(code="010", swift_code="NLCBTZTX", name="NBC Bank", supports_rtgs=True, supports_eft=True, supports_tips=True),
    BankDefinition(code="030", swift_code="SBICTZTX", name="Stanbic Bank Tanzania", supports_rtgs=True, supports_eft=True, supports_tips=False),
    BankDefinition(code="020", swift_code="EQBLTZTZ", name="Equity Bank Tanzania", supports_rtgs=True, supports_eft=True, supports_tips=True),
]

TRANSFER_TYPES = ["rtgs", "eft", "tips", "internal"]

SETTLEMENT_RULES = {
    "rtgs": {"same_day_cutoff": "15:00", "timezone": "Africa/Dar_es_Salaam", "settlement": "same_day"},
    "eft": {"same_day_cutoff": None, "timezone": "Africa/Dar_es_Salaam", "settlement": "next_business_day"},
    "tips": {"same_day_cutoff": None, "timezone": "Africa/Dar_es_Salaam", "settlement": "instant"},
}

# Tanzanian bank account numbers are typically 10-13 digits.
ACCOUNT_REFERENCE_FORMAT = r"^\d{10,13}$"

_BY_CODE = {b.code: b for b in SUPPORTED_BANKS}


def get_bank(code: str) -> BankDefinition | None:
    return _BY_CODE.get(code)
