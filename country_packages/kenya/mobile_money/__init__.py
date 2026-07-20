"""
Kenya Country Package - Mobile Money

M-Pesa and Airtel Money: authentication shape, IPN/callback formats,
webhook validation, status codes, settlement behaviour, supported
operations and currency rules. The Data Mapping module (mappings/)
turns these raw payloads into Orbit Canonical Events - this module only
describes the provider's own shape.
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
    currency: str = "KES"


MOBILE_MONEY_PROVIDERS: list[MobileMoneyDefinition] = [
    MobileMoneyDefinition(
        provider="mpesa",
        display_name="M-Pesa",
        ipn_format="mpesa_ipn",
        webhook_signature_header=None,  # Daraja validates by source IP allowlist, not a signature header
        status_codes={
            "0": "success",
            "1": "insufficient_funds",
            "1032": "cancelled_by_user",
            "1037": "timeout",
            "2001": "invalid_pin",
        },
        settlement="instant",
        supported_operations=["stk_push", "c2b", "b2c", "b2b", "balance_query", "transaction_status"],
    ),
    MobileMoneyDefinition(
        provider="airtel_money",
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
