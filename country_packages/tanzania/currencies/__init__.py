"""Tanzania Country Package - Currency"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CurrencyDefinition:
    code: str
    symbol: str
    decimal_places: int
    name: str


CURRENCY = CurrencyDefinition(code="TZS", symbol="TSh", decimal_places=0, name="Tanzanian Shilling")
