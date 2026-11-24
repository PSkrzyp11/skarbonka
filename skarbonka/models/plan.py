"""Planowanie: budżety miesięczne i cele oszczędnościowe."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_UP, Decimal

from skarbonka.models.enums import StanBudzetu
from skarbonka.models.transakcja import ZERO
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


@dataclass
class WplataCelu:
    """Kwota odłożona na cel."""

    cel_id: int
    data: date
    kwota: Decimal
    id: int | None = None

    def __post_init__(self) -> None:
        if self.kwota <= 0:
            raise NieprawidlowaKwota("Wpłata musi być dodatnia.")


@dataclass
class Cel:
    """Kwota, którą użytkownik chce odłożyć do podanego dnia.

    Wpłaty na cel są wirtualne, nie zmieniają sald kont.
    """

    nazwa: str
    kwota_docelowa: Decimal
    termin: date
    odlozono: Decimal = ZERO
    id: int | None = None

    def __post_init__(self) -> None:
        if self.kwota_docelowa <= 0:
            raise NieprawidlowaKwota("Kwota celu musi być dodatnia.")

    @property
    def procent(self) -> float:
        """Zwraca, jaki procent celu już odłożono."""
        return float(self.odlozono / self.kwota_docelowa * 100)

    @property
    def brakuje(self) -> Decimal:
        """Zwraca brakującą kwotę, a po osiągnięciu celu zero."""
        return max(self.kwota_docelowa - self.odlozono, ZERO)

    def rata(self, dzis: date) -> Decimal:
        """Zwraca kwotę, którą trzeba odkładać co miesiąc, by zdążyć."""
        miesiace = (self.termin.year - dzis.year) * 12 + self.termin.month - dzis.month
        return (self.brakuje / max(miesiace, 1)).quantize(Decimal("0.01"), rounding=ROUND_UP)

    def __str__(self) -> str:
        return self.nazwa
