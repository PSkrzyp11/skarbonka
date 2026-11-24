"""Transakcje: klasa bazowa oraz jej rodzaje."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import ClassVar

from skarbonka.utils.formatowanie import formatuj_date, formatuj_kwote
from skarbonka.wyjatki import BladWalidacji, NieprawidlowaKwota

ZERO = Decimal("0.00")


@dataclass
class Transakcja(ABC):
    """Wspólna część wszystkich transakcji.

    Kwota jest zawsze dodatnia. O tym, czy zwiększa, czy zmniejsza stan
    pieniędzy, decyduje klasa pochodna.
    """

    RODZAJ: ClassVar[str] = ""
    ZNAK: ClassVar[str] = ""

    data: date
    kwota: Decimal
    opis: str
    konto_id: int
    kategoria_id: int | None = None
    id: int | None = None
    import_id: int | None = None

    def __post_init__(self) -> None:
        """Pilnuje poprawności kwoty niezależnie od tego, kto tworzy obiekt."""
        if self.kwota <= 0:
            raise NieprawidlowaKwota("Kwota transakcji musi być dodatnia.")

    @property
    @abstractmethod
    def wplyw(self) -> Decimal:
        """Zmiana łącznego stanu pieniędzy na wszystkich kontach."""

    @property
    def odcisk(self) -> tuple[date, Decimal, str, int]:
        """Cechy, po których poznaje się tę samą operację w dwóch wyciągach."""
        return (self.data, self.wplyw, self.opis.casefold(), self.konto_id)

    def wplyw_na_konto(self, konto_id: int) -> Decimal:
        """Zmiana salda jednego, wybranego konta."""
        return self.wplyw if konto_id == self.konto_id else ZERO

    def dotyczy_konta(self, konto_id: int) -> bool:
        """Informuje, czy transakcja jest związana z podanym kontem."""
        return konto_id == self.konto_id

    def __str__(self) -> str:
        numer = self.id or "-"
        kwota = self.ZNAK + formatuj_kwote(self.kwota)
        return f"{numer:>4}  {formatuj_date(self.data)}  {self.RODZAJ:<9}{kwota:>16}  {self.opis}"


class Wydatek(Transakcja):
    """Pieniądze, które ubyły."""

    RODZAJ = "wydatek"
    ZNAK = "-"

    @property
    def wplyw(self) -> Decimal:
        return -self.kwota


class Przychod(Transakcja):
    """Pieniądze, które przybyły."""

    RODZAJ = "przychód"
    ZNAK = "+"

    @property
    def wplyw(self) -> Decimal:
        return self.kwota


@dataclass
class Przelew(Transakcja):
    """Przesunięcie pieniędzy między własnymi kontami."""

    RODZAJ: ClassVar[str] = "przelew"

    konto_docelowe_id: int = field(kw_only=True)

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.konto_id == self.konto_docelowe_id:
            raise BladWalidacji("Przelew wymaga dwóch różnych kont.")

    @property
    def wplyw(self) -> Decimal:
        return ZERO

    def wplyw_na_konto(self, konto_id: int) -> Decimal:
        if konto_id == self.konto_id:
            return -self.kwota
        if konto_id == self.konto_docelowe_id:
            return self.kwota
        return ZERO

    def dotyczy_konta(self, konto_id: int) -> bool:
        return konto_id in (self.konto_id, self.konto_docelowe_id)
