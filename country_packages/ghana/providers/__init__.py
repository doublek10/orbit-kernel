"""
Ghana Country Package - Providers

Every financial provider available to a Ghanaian company, same shape as
Kenya's providers module (authentication, webhook format, health check,
refresh strategy, supported events, required credentials, rate limits).
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
        provider="mtn_momo_gh",
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
        provider="vodafone_cash",
        display_name="Vodafone Cash (Telecel Cash)",
        category="mobile_money",
        auth_method="api_key",
        credential_fields=["api_key", "merchant_code"],
        webhook_format="vodafone_callback",
        health_check="live_ping",
        refresh_strategy="webhook",
        supported_events=["payment.vodafone_cash.received", "payment.vodafone_cash.failed"],
        rate_limit_per_minute=120,
    ),
    ProviderDefinition(
        provider="airteltigo_money",
        display_name="AirtelTigo Money",
        category="mobile_money",
        auth_method="api_key",
        credential_fields=["api_key"],
        webhook_format="airteltigo_callback",
        health_check="live_ping",
        refresh_strategy="webhook",
        supported_events=["payment.airteltigo.received", "payment.airteltigo.failed"],
        rate_limit_per_minute=120,
    ),
    ProviderDefinition(
        provider="gcb_bank",
        display_name="GCB Bank",
        category="bank",
        auth_method="api_key",
        credential_fields=["api_key", "api_secret"],
        webhook_format="gcb_webhook",
        health_check="credential_shape",
        refresh_strategy="scheduled",
        supported_events=["payment.bank.completed", "payment.bank.reversed"],
        rate_limit_per_minute=60,
    ),
    ProviderDefinition(
        provider="ecobank_gh",
        display_name="Ecobank Ghana",
        category="bank",
        auth_method="api_key",
        credential_fields=["api_key", "api_secret"],
        webhook_format="ecobank_webhook",
        health_check="credential_shape",
        refresh_strategy="scheduled",
        supported_events=["payment.bank.completed", "payment.bank.reversed"],
        rate_limit_per_minute=60,
    ),
    ProviderDefinition(
        provider="paystack",
        display_name="Paystack",
        category="payment_gateway",
        auth_method="api_key",
        credential_fields=["public_key", "secret_key"],
        webhook_format="paystack_webhook",
        health_check="live_ping",
        refresh_strategy="webhook",
        supported_events=["payment.gateway.received", "payment.gateway.failed"],
        rate_limit_per_minute=180,
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
