"""Uganda Country Package - Crypto Providers"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CryptoProviderDefinition:
    provider: str
    display_name: str
    supported_assets: list[str]
    settlement: str


CRYPTO_PROVIDERS: list[CryptoProviderDefinition] = [
    CryptoProviderDefinition(
        provider="binance_pay",
        display_name="Binance Pay",
        supported_assets=["USDT", "BTC", "BNB"],
        settlement="instant",
    ),
]

_BY_PROVIDER = {p.provider: p for p in CRYPTO_PROVIDERS}


def get_crypto_provider(provider: str) -> CryptoProviderDefinition | None:
    return _BY_PROVIDER.get(provider)
