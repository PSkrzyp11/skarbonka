"""Kurs waluty z jednego dnia."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from skarbonka.wyjatki import BladKursu

GROSZ = Decimal("0.01")


@dataclass
class Kurs:
    """Cena jednej jednostki waluty w złotych."""

    waluta: str
    data: date
    wartosc: Decimal
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.wartosc.is_finite() or self.wartosc <= 0:
            raise BladKursu(f"Niepoprawny kurs {self.waluta}: {self.wartosc}.")

    def przelicz(self, kwota: Decimal) -> Decimal:
        """Zamienia kwotę w walucie na złote, z zaokrągleniem do grosza."""
        return (kwota * self.wartosc).quantize(GROSZ, rounding=ROUND_HALF_UP)
