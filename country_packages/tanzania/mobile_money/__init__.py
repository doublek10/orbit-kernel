"""
Tanzania Country Package - Mobile Money

M-Pesa (Vodacom), Tigo Pesa (Mixx by Yas) and HaloPesa (Halotel):
authentication shape, callback formats, status codes, settlement
behaviour and supported operations. mappings/ turns these into Orbit
Canonical Events.
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
    currency: str = "TZS"


MOBILE_MONEY_PROVIDERS: list[MobileMoneyDefinition] = [
    MobileMoneyDefinition(
        provider="mpesa_tz",
        display_name="M-Pesa (Vodacom)",
        ipn_format="mpesa_tz_callback",
        webhook_signature_header=None,  # source IP allowlist, same as Kenya's Daraja
        status_codes={
            "0": "success",
            "1": "insufficient_funds",
            "1032": "cancelled_by_user",
            "1037": "timeout",
        },
        settlement="instant",
        supported_operations=["stk_push", "c2b", "b2c", "balance_query", "transaction_status"],
    ),
    MobileMoneyDefinition(
        provider="tigo_pesa",
        display_name="Tigo Pesa (Mixx by Yas)",
        ipn_format="tigo_pesa_callback",
        webhook_signature_header="X-Tigo-Signature",
        status_codes={
            "200": "success",
            "400": "failed",
            "408": "timeout",
        },
        settlement="instant",
        supported_operations=["collection", "disbursement", "transaction_status"],
    ),
    MobileMoneyDefinition(
        provider="halopesa",
        display_name="HaloPesa (Halotel)",
        ipn_format="halopesa_callback",
        webhook_signature_header=None,
        status_codes={
            "SUCCESS": "success",
            "FAILED": "failed",
            "PENDING": "pending",
        },
        settlement="instant",
        supported_operations=["collection", "disbursement", "transaction_status"],
    ),
]

_BY_PROVIDER = {p.provider: p for p in MOBILE_MONEY_PROVIDERS}


def get_mobile_money_provider(provider: str) -> MobileMoneyDefinition | None:
    return _BY_PROVIDER.get(provider)
