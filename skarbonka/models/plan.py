"""Planowanie: budżety miesięczne."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from skarbonka.models.enums import StanBudzetu
from skarbonka.wyjatki import NieprawidlowaKwota


@dataclass
class Budzet:
    """Limit wydatków w kategorii na jeden miesiąc."""

    kategoria_id: int
    miesiac: date
    limit: Decimal
    id: int | None = None

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise NieprawidlowaKwota("Limit budżetu musi być dodatni.")

    def procent(self, wydano: Decimal) -> float:
        """Zwraca, jaki procent limitu wykorzystano."""
        return float(wydano / self.limit * 100)

    def stan(self, wydano: Decimal, prog: int = 80) -> StanBudzetu:
        """Ocenia wykorzystanie limitu. Próg to procent, od którego ostrzegamy."""
        procent = self.procent(wydano)
        if procent > 100:
            return StanBudzetu.PRZEKROCZONY
        if procent >= prog:
            return StanBudzetu.UWAGA
        return StanBudzetu.W_NORMIE
