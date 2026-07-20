"""
Uganda Country Package - Providers

Every financial provider available to a Ugandan company, same shape as
Kenya's and Ghana's providers modules.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderDefinition:
    provider: str
    display_name: str
    category: str  # bank | mobile_money | payment_gateway | crypto
    auth_method: str  # api_key | oauth | none
    credential_fields: list[str] = field(default_factory=list)
    webhook_format: str = "json"
    health_check: str = "credential_shape"  # credential_shape | live_ping
    refresh_strategy: str = "manual"  # manual | scheduled | webhook
    supported_events: list[str] = field(default_factory=list)
    rate_limit_per_minute: int | None = None
    live: bool = False


PROVIDERS: list[ProviderDefinition] = [
    ProviderDefinition(
        provider="mtn_momo_ug",
        display_name="MTN Mobile Money",
        category="mobile_money",
        auth_method="oauth",
        credential_fields=["subscription_key", "api_user", "api_key"],
        webhook_format="mtn_momo_callback",
        health_check="live_ping",
        refresh_strategy="webhook",
        supported_events=["payment.mtn_momo.received", "payment.mtn_momo.failed"],
        rate_limit_per_minute=300,
    ),
    ProviderDefinition(
        provider="airtel_money_ug",
        display_name="Airtel Money",
        category="mobile_money",
        auth_method="api_key",
        credential_fields=["api_key"],
        webhook_format="airtel_callback",
        health_check="live_ping",
        refresh_strategy="webhook",
        supported_events=["payment.airtel.received", "payment.airtel.failed"],
        rate_limit_per_minute=120,
    ),
    ProviderDefinition(
        provider="stanbic_bank_ug",
        display_name="Stanbic Bank Uganda",
        category="bank",
        auth_method="api_key",
        credential_fields=["api_key", "api_secret"],
        webhook_format="stanbic_webhook",
        health_check="credential_shape",
        refresh_strategy="scheduled",
        supported_events=["payment.bank.completed", "payment.bank.reversed"],
        rate_limit_per_minute=60,
    ),
    ProviderDefinition(
        provider="centenary_bank",
        display_name="Centenary Bank",
        category="bank",
        auth_method="api_key",
        credential_fields=["api_key", "api_secret"],
        webhook_format="centenary_webhook",
        health_check="credential_shape",
        refresh_strategy="scheduled",
        supported_events=["payment.bank.completed", "payment.bank.reversed"],
        rate_limit_per_minute=60,
    ),
    ProviderDefinition(
        provider="flutterwave",
        display_name="Flutterwave",
        category="payment_gateway",
        auth_method="api_key",
        credential_fields=["public_key", "secret_key"],
        webhook_format="flutterwave_webhook",
        health_check="live_ping",
        refresh_strategy="webhook",
        supported_events=["payment.gateway.received", "payment.gateway.failed"],
        rate_limit_per_minute=180,
    ),
    ProviderDefinition(
        provider="binance_pay",
        display_name="Binance Pay",
        category="crypto",
        auth_method="api_key",
        credential_fields=["api_key", "api_secret"],
        webhook_format="binance_webhook",
        health_check="credential_shape",
        refresh_strategy="webhook",
        supported_events=["payment.crypto.received"],
        rate_limit_per_minute=60,
    ),
    ProviderDefinition(
        provider="mock_mobile_money",
        display_name="Sandbox Mobile Money",
        category="mobile_money",
        auth_method="none",
        credential_fields=[],
        webhook_format="json",
        health_check="live_ping",
        refresh_strategy="webhook",
        supported_events=["payment.received"],
        live=True,
    ),
]

_BY_PROVIDER = {p.provider: p for p in PROVIDERS}


def get_provider(provider: str) -> ProviderDefinition | None:
    return _BY_PROVIDER.get(provider)
