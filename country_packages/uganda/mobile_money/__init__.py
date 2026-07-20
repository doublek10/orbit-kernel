"""
Uganda Country Package - Mobile Money

MTN Mobile Money and Airtel Money: authentication shape, callback
formats, status codes, settlement behaviour and supported operations.
mappings/ turns these into Orbit Canonical Events.
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
    currency: str = "UGX"


MOBILE_MONEY_PROVIDERS: list[MobileMoneyDefinition] = [
    MobileMoneyDefinition(
        provider="mtn_momo_ug",
        display_name="MTN Mobile Money",
        ipn_format="mtn_momo_callback",
        webhook_signature_header="X-Callback-Signature",
        status_codes={
            "SUCCESSFUL": "success",
            "FAILED": "failed",
            "PENDING": "pending",
            "REJECTED": "cancelled_by_user",
        },
        settlement="instant",
        supported_operations=["request_to_pay", "disbursement", "transaction_status"],
    ),
    MobileMoneyDefinition(
        provider="airtel_money_ug",
        display_name="Airtel Money",
        ipn_format="airtel_callback",
        webhook_signature_header="X-Airtel-Signature",
        status_codes={
            "TS": "success",
            "TF": "failed",
            "TA": "ambiguous_pending",
        },
        settlement="instant",
        supported_operations=["collection", "disbursement", "transaction_status"],
    ),
]

_BY_PROVIDER = {p.provider: p for p in MOBILE_MONEY_PROVIDERS}


def get_mobile_money_provider(provider: str) -> MobileMoneyDefinition | None:
    return _BY_PROVIDER.get(provider)
