"""Ghana Country Package - Currency"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CurrencyDefinition:
    code: str
    symbol: str
    decimal_places: int
    name: str


CURRENCY = CurrencyDefinition(code="GHS", symbol="GH₵", decimal_places=2, name="Ghanaian Cedi")
