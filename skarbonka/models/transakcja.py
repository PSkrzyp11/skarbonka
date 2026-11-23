"""Transakcje: klasa bazowa oraz jej rodzaje."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from skarbonka.utils.formatowanie import formatuj_date, formatuj_kwote
from skarbonka.wyjatki import NieprawidlowaKwota


@dataclass
class Transakcja(ABC):
    """Wspólna część wszystkich transakcji.

    Kwota jest zawsze dodatnia. O tym, czy zwiększa, czy zmniejsza saldo,
    decyduje klasa pochodna.
    """

    data: date
    kwota: Decimal
    opis: str
    id: int | None = None

    def __post_init__(self) -> None:
        """Pilnuje poprawności kwoty niezależnie od tego, kto tworzy obiekt."""
        if self.kwota <= 0:
            raise NieprawidlowaKwota("Kwota transakcji musi być dodatnia.")

    @property
    @abstractmethod
    def wplyw(self) -> Decimal:
        """Zmiana salda spowodowana transakcją."""

    def __str__(self) -> str:
        kwota = formatuj_kwote(self.wplyw, ze_znakiem=True)
        return f"{formatuj_date(self.data)}  {kwota:>16}  {self.opis}"


class Wydatek(Transakcja):
    """Pieniądze, które ubyły."""

    @property
    def wplyw(self) -> Decimal:
        return -self.kwota


class Przychod(Transakcja):
    """Pieniądze, które przybyły."""

    @property
    def wplyw(self) -> Decimal:
        return self.kwota
