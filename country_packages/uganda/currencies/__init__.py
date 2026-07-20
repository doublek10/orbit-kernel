"""Uganda Country Package - Currency"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CurrencyDefinition:
    code: str
    symbol: str
    decimal_places: int
    name: str


CURRENCY = CurrencyDefinition(code="UGX", symbol="USh", decimal_places=0, name="Ugandan Shilling")
