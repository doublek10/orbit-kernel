"""
Kenya Country Package - Banking

Banking knowledge for Kenya: which banks are supported, settlement
rules, transfer types, reference formats and bank codes. The Rule
Engine / Provider Manager consume this - nothing here is hardcoded
anywhere in kernel/.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BankDefinition:
    code: str  # Kenya Bankers Association clearing code
    swift_code: str
    name: str
    supports_rtgs: bool
    supports_eft: bool
    supports_pesalink: bool


SUPPORTED_BANKS: list[BankDefinition] = [
    BankDefinition(code="01", swift_code="KCBLKENX", name="KCB Bank", supports_rtgs=True, supports_eft=True, supports_pesalink=True),
    BankDefinition(code="68", swift_code="EQBLKENA", name="Equity Bank", supports_rtgs=True, supports_eft=True, supports_pesalink=True),
    BankDefinition(code="11", swift_code="BARCKENX", name="Absa Bank Kenya", supports_rtgs=True, supports_eft=True, supports_pesalink=True),
    BankDefinition(code="02", swift_code="SBICKENX", name="Standard Chartered Kenya", supports_rtgs=True, supports_eft=True, supports_pesalink=False),
    BankDefinition(code="03", swift_code="SBICKENX", name="Standard Bank / Stanbic Kenya", supports_rtgs=True, supports_eft=True, supports_pesalink=True),
]

TRANSFER_TYPES = ["rtgs", "eft", "pesalink", "internal"]

# RTGS cutoff and same-day settlement window - consumed by the Workflow
# Engine when deciding whether a bank transfer settles same-day.
SETTLEMENT_RULES = {
    "rtgs": {"same_day_cutoff": "15:00", "timezone": "Africa/Nairobi", "settlement": "same_day"},
    "eft": {"same_day_cutoff": None, "timezone": "Africa/Nairobi", "settlement": "next_business_day"},
    "pesalink": {"same_day_cutoff": None, "timezone": "Africa/Nairobi", "settlement": "instant"},
}

# Kenyan bank account references are typically 6-17 digits.
ACCOUNT_REFERENCE_FORMAT = r"^\d{6,17}$"

_BY_CODE = {b.code: b for b in SUPPORTED_BANKS}


def get_bank(code: str) -> BankDefinition | None:
    return _BY_CODE.get(code)
