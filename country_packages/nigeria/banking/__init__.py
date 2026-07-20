"""Nigeria Country Package - Banking"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BankDefinition:
    code: str  # Nigeria Interbank Settlement System (NIBSS) bank code
    swift_code: str
    name: str
    supports_rtgs: bool  # NEFT / NIBSS real-time gross settlement
    supports_nip: bool  # NIBSS Instant Payment
    supports_ussd: bool


SUPPORTED_BANKS: list[BankDefinition] = [
    BankDefinition(code="058", swift_code="GTBINGLA", name="Guaranty Trust Bank", supports_rtgs=True, supports_nip=True, supports_ussd=True),
    BankDefinition(code="044", swift_code="ABNGNGLA", name="Access Bank", supports_rtgs=True, supports_nip=True, supports_ussd=True),
    BankDefinition(code="057", swift_code="ZEIBNGLA", name="Zenith Bank", supports_rtgs=True, supports_nip=True, supports_ussd=True),
    BankDefinition(code="011", swift_code="FBNINGLA", name="First Bank of Nigeria", supports_rtgs=True, supports_nip=True, supports_ussd=True),
    BankDefinition(code="033", swift_code="UNAFNGLA", name="United Bank for Africa", supports_rtgs=True, supports_nip=True, supports_ussd=True),
]

TRANSFER_TYPES = ["rtgs", "nip", "ussd", "internal"]

SETTLEMENT_RULES = {
    "rtgs": {"same_day_cutoff": "14:00", "timezone": "Africa/Lagos", "settlement": "same_day"},
    "nip": {"same_day_cutoff": None, "timezone": "Africa/Lagos", "settlement": "instant"},
    "ussd": {"same_day_cutoff": None, "timezone": "Africa/Lagos", "settlement": "instant"},
}

# NUBAN account numbers are exactly 10 digits.
ACCOUNT_REFERENCE_FORMAT = r"^\d{10}$"

_BY_CODE = {b.code: b for b in SUPPORTED_BANKS}


def get_bank(code: str) -> BankDefinition | None:
    return _BY_CODE.get(code)
