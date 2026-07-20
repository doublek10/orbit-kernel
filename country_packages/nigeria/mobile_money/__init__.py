"""
Nigeria Country Package - Mobile Money

OPay, PalmPay and Paga: authentication shape, callback formats, status
codes, settlement behaviour and supported operations. mappings/ turns
these into Orbit Canonical Events. These operate as licensed Mobile
Money Operators / PSBs rather than telco-issued wallets - the shape the
Kernel cares about (webhook -> canonical event) is the same either way.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MobileMoneyDefinition:
    provider: str
    display_name: str
    ipn_format: str
    webhook_signature_header: str | None
    status_codes: dict[str, str]
    settlement: str  # instant | t_plus_1
    supported_operations: list[str] = field(default_factory=list)
    currency: str = "NGN"


MOBILE_MONEY_PROVIDERS: list[MobileMoneyDefinition] = [
    MobileMoneyDefinition(
        provider="opay",
        display_name="OPay",
        ipn_format="opay_callback",
        webhook_signature_header="Authorization",
        status_codes={
            "SUCCESS": "success",
            "FAIL": "failed",
            "PENDING": "pending",
            "CLOSE": "cancelled_by_user",
        },
        settlement="instant",
        supported_operations=["collection", "disbursement", "transaction_status"],
    ),
    MobileMoneyDefinition(
        provider="palmpay",
        display_name="PalmPay",
        ipn_format="palmpay_callback",
        webhook_signature_header="Signature",
        status_codes={
            "00000000": "success",
            "00000001": "failed",
            "00000002": "pending",
        },
        settlement="instant",
        supported_operations=["collection", "disbursement", "transaction_status"],
    ),
    MobileMoneyDefinition(
        provider="paga",
        display_name="Paga",
        ipn_format="paga_callback",
        webhook_signature_header="X-Paga-Signature",
        status_codes={
            "0": "success",
            "1": "failed",
            "2": "pending",
        },
        settlement="instant",
        supported_operations=["collection", "disbursement", "transaction_status"],
    ),
]

_BY_PROVIDER = {p.provider: p for p in MOBILE_MONEY_PROVIDERS}


def get_mobile_money_provider(provider: str) -> MobileMoneyDefinition | None:
    return _BY_PROVIDER.get(provider)
