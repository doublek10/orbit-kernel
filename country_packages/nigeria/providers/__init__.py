"""
Nigeria Country Package - Providers

Every financial provider available to a Nigerian company, same shape
as Kenya's, Ghana's, Uganda's and Tanzania's providers modules.
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
        provider="opay",
        display_name="OPay",
        category="mobile_money",
        auth_method="api_key",
        credential_fields=["merchant_id", "public_key", "secret_key"],
        webhook_format="opay_callback",
        health_check="live_ping",
        refresh_strategy="webhook",
        supported_events=["payment.opay.received", "payment.opay.failed"],
        rate_limit_per_minute=300,
    ),
    ProviderDefinition(
        provider="palmpay",
        display_name="PalmPay",
        category="mobile_money",
        auth_method="api_key",
        credential_fields=["app_id", "public_key", "private_key"],
        webhook_format="palmpay_callback",
        health_check="live_ping",
        refresh_strategy="webhook",
        supported_events=["payment.palmpay.received", "payment.palmpay.failed"],
        rate_limit_per_minute=200,
    ),
    ProviderDefinition(
        provider="paga",
        display_name="Paga",
        category="mobile_money",
        auth_method="api_key",
        credential_fields=["principal", "credential", "public_key"],
        webhook_format="paga_callback",
        health_check="live_ping",
        refresh_strategy="webhook",
        supported_events=["payment.paga.received", "payment.paga.failed"],
        rate_limit_per_minute=150,
    ),
    ProviderDefinition(
        provider="gtbank",
        display_name="Guaranty Trust Bank",
        category="bank",
        auth_method="api_key",
        credential_fields=["api_key", "api_secret"],
        webhook_format="gtbank_webhook",
        health_check="credential_shape",
        refresh_strategy="scheduled",
        supported_events=["payment.bank.completed", "payment.bank.reversed"],
        rate_limit_per_minute=60,
    ),
    ProviderDefinition(
        provider="access_bank",
        display_name="Access Bank",
        category="bank",
        auth_method="api_key",
        credential_fields=["api_key", "api_secret"],
        webhook_format="access_bank_webhook",
        health_check="credential_shape",
        refresh_strategy="scheduled",
        supported_events=["payment.bank.completed", "payment.bank.reversed"],
        rate_limit_per_minute=60,
    ),
    ProviderDefinition(
        provider="zenith_bank",
        display_name="Zenith Bank",
        category="bank",
        auth_method="api_key",
        credential_fields=["api_key", "api_secret"],
        webhook_format="zenith_webhook",
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
