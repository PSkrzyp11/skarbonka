"""Bilans stałych pozycji i podział wspólnych między osoby."""

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from skarbonka.models.cykliczna import GROSZ, Cykliczna
from skarbonka.models.enums import StanPlatnosci
from skarbonka.models.transakcja import ZERO, Transakcja

SREDNIO_DNI_W_MIESIACU = 30


def podziel(kwota: Decimal, na_ile: int) -> list[Decimal]:
    """Dzieli kwotę po równo. Grosze, których nie da się podzielić, dostają pierwsi."""
    znak = -1 if kwota < 0 else 1
    grosze, reszta = divmod(int(abs(kwota) / GROSZ), na_ile)
    return [znak * GROSZ * (grosze + (numer < reszta)) for numer in range(na_ile)]


@dataclass(frozen=True)
class BilansStalych:
    """Stałe przychody i opłaty w przeliczeniu na jeden miesiąc."""

    przychody: Decimal
    wydatki: Decimal

    @property
    def na_czysto(self) -> Decimal:
        """Zwraca kwotę, która zostaje po opłaceniu wszystkiego."""
        return self.przychody - self.wydatki

    @property
    def dziennie(self) -> Decimal:
        """Zwraca kwotę na czysto podzieloną na 30 dni."""
        return (self.na_czysto / SREDNIO_DNI_W_MIESIACU).quantize(GROSZ)

    @property
    def procent(self) -> float | None:
        """Zwraca, jaki procent przychodów zostaje. None, gdy przychodów nie ma."""
        if self.przychody == 0:
            return None
        return float(self.na_czysto / self.przychody * 100)


@dataclass(frozen=True)
class Udzial:
    """Część stałej pozycji, która przypada na osobę. Domyślnie cała pozycja."""

    cykliczna: Cykliczna
    numer: int = 0
    na_ile: int = 1
    wspolny: bool = False

    def czesc(self, kwota: Decimal) -> Decimal:
        """Zwraca część podanej kwoty."""
        return podziel(kwota, self.na_ile)[self.numer]

    @property
    def wplyw(self) -> Decimal:
        """Zwraca część jednej płatności."""
        return self.czesc(self.cykliczna.wplyw)

    @property
    def miesiecznie(self) -> Decimal:
        """Zwraca część przeliczoną na miesiąc."""
        return self.czesc(self.cykliczna.miesiecznie)

    @property
    def ulamek(self) -> str:
        """Zwraca podział jako tekst, np. 1/2."""
        return f"1/{self.na_ile}"


def policz_bilans(udzialy: Iterable[Udzial]) -> BilansStalych:
    """Zwraca miesięczny bilans aktywnych pozycji."""
    kwoty = [u.miesiecznie for u in udzialy if u.cykliczna.aktywna]
    return BilansStalych(
        przychody=sum((k for k in kwoty if k > 0), ZERO),
        wydatki=-sum((k for k in kwoty if k < 0), ZERO),
    )


@dataclass(frozen=True)
class Platnosc:
    """Jeden termin stałej pozycji w harmonogramie."""

    cykliczna: Cykliczna
    termin: date
    stan: StanPlatnosci
    transakcja: Transakcja | None = None
    udzial: Udzial | None = None

    @property
    def wplyw(self) -> Decimal:
        """Zwraca kwotę zaksięgowaną, a przed zaksięgowaniem przewidywaną.

        Przy płatności wspólnej oglądanej u osoby jest to tylko jej część.
        """
        zrodlo = self.cykliczna if self.transakcja is None else self.transakcja
        return zrodlo.wplyw if self.udzial is None else self.udzial.czesc(zrodlo.wplyw)

    @property
    def wspolna(self) -> bool:
        """Czy to część płatności wspólnej."""
        return self.udzial is not None and self.udzial.wspolny

    @property
    def do_poprawy(self) -> bool:
        """Czy można poprawić kwotę: ostatni zaksięgowany termin zmiennej pozycji."""
        ostatni = self.termin == self.cykliczna.ostatnia
        return self.cykliczna.zmienna and ostatni and self.transakcja is not None

    @property
    def kolejna(self) -> bool:
        """Czy to najbliższy niezaksięgowany termin swojej pozycji."""
        return self.termin == self.cykliczna.nastepny


def do_zaplaty(platnosci: Iterable[Platnosc]) -> Decimal:
    """Zwraca sumę opłat z harmonogramu, które nie są jeszcze załatwione."""
    czekajace = [p.wplyw for p in platnosci if p.stan is not StanPlatnosci.ZALATWIONA]
    return -sum((kwota for kwota in czekajace if kwota < 0), ZERO)


@dataclass(frozen=True)
class GrupaStalych:
    """Pozycje jednej osoby razem z jej częścią wspólnych, wspólne albo wszystkie."""

    nazwa: str
    osoba_id: int | None
    udzialy: list[Udzial]

    @property
    def wlasne(self) -> list[Udzial]:
        """Zwraca pozycje bez części wspólnych."""
        return [u for u in self.udzialy if not u.wspolny]

    @property
    def wspolne(self) -> list[Udzial]:
        """Zwraca części wspólnych pozycji."""
        return [u for u in self.udzialy if u.wspolny]

    @property
    def bilans(self) -> BilansStalych:
        """Zwraca bilans tej grupy."""
        return policz_bilans(self.udzialy)

    def platnosci(self, harmonogram: list[Platnosc]) -> list[Platnosc]:
        """Zwraca płatności tej grupy, wspólne w części osoby."""
        udzialy = {u.cykliczna.id: u for u in self.udzialy}
        return [
            replace(p, udzial=udzialy[p.cykliczna.id])
            for p in harmonogram
            if p.cykliczna.id in udzialy
        ]
