"""Nigeria Country Package - Payment Gateways"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PaymentGatewayDefinition:
    provider: str
    display_name: str
    supported_currencies: list[str]
    webhook_format: str
    settlement: str


PAYMENT_GATEWAYS: list[PaymentGatewayDefinition] = [
    PaymentGatewayDefinition(
        provider="paystack",
        display_name="Paystack",
        supported_currencies=["NGN", "USD"],
        webhook_format="paystack_webhook",
        settlement="t_plus_1",
    ),
    PaymentGatewayDefinition(
        provider="flutterwave",
        display_name="Flutterwave",
        supported_currencies=["NGN", "USD"],
        webhook_format="flutterwave_webhook",
        settlement="t_plus_1",
    ),
]

_BY_PROVIDER = {p.provider: p for p in PAYMENT_GATEWAYS}


def get_payment_gateway(provider: str) -> PaymentGatewayDefinition | None:
    return _BY_PROVIDER.get(provider)
