"""Transakcje: zapis, filtrowanie, sortowanie i sumowanie."""

from collections.abc import Callable, Iterator
from datetime import date
from decimal import Decimal

from skarbonka.models.transakcja import ZERO, Przychod, Transakcja, Wydatek
from skarbonka.storage.repozytoria import Repozytorium
from skarbonka.wyjatki import BladWalidacji

SORTOWANIA: dict[str, tuple[Callable[[Transakcja], tuple], bool]] = {
    "od najnowszych": (lambda t: (t.data, t.id), True),
    "od najstarszych": (lambda t: (t.data, t.id), False),
    "od największych kwot": (lambda t: (t.kwota, t.id), True),
    "od najmniejszych kwot": (lambda t: (t.kwota, t.id), False),
}


class SerwisTransakcji:
    """Zapis i wyszukiwanie transakcji."""

    def __init__(self, transakcje: Repozytorium[Transakcja]) -> None:
        self._transakcje = transakcje

    def wszystkie(self) -> list[Transakcja]:
        """Zwraca wszystkie transakcje."""
        return self._transakcje.wszystkie()

    def pobierz(self, numer: int) -> Transakcja:
        """Zwraca transakcję o podanym numerze."""
        return self._transakcje.pobierz(numer)

    def dodaj(self, transakcja: Transakcja) -> Transakcja:
        """Zapisuje nową transakcję."""
        return self._transakcje.dodaj(transakcja)

    def zmien(self, transakcja: Transakcja) -> None:
        """Zapisuje zmienioną transakcję."""
        self._transakcje.zmien(transakcja)

    def usun(self, transakcja: Transakcja) -> None:
        """Usuwa transakcję."""
        self._transakcje.usun(transakcja.id)

    def filtruj(
        self,
        od: date | None = None,
        do: date | None = None,
        konto_id: int | None = None,
        kategoria_id: int | None = None,
        fraza: str = "",
    ) -> list[Transakcja]:
        """Zwraca transakcje spełniające wszystkie podane warunki."""
        if od is not None and do is not None and od > do:
            raise BladWalidacji("Data początkowa jest późniejsza niż końcowa.")

        warunki: list[Callable[[Transakcja], bool]] = []
        if od is not None:
            warunki.append(lambda t: t.data >= od)
        if do is not None:
            warunki.append(lambda t: t.data <= do)
        if konto_id is not None:
            warunki.append(lambda t: t.dotyczy_konta(konto_id))
        if kategoria_id is not None:
            warunki.append(lambda t: t.kategoria_id == kategoria_id)
        if fraza:
            warunki.append(lambda t: fraza.casefold() in t.opis.casefold())
        return [t for t in self.wszystkie() if all(warunek(t) for warunek in warunki)]


def posortuj(transakcje: list[Transakcja], sposob: str = "od najnowszych") -> list[Transakcja]:
    """Zwraca nową listę posortowaną wybranym sposobem."""
    klucz, malejaco = SORTOWANIA[sposob]
    return sorted(transakcje, key=klucz, reverse=malejaco)


def strony(transakcje: list[Transakcja], rozmiar: int = 20) -> Iterator[list[Transakcja]]:
    """Generator: oddaje kolejne porcje listy, po jednej na żądanie."""
    for poczatek in range(0, len(transakcje), rozmiar):
        yield transakcje[poczatek : poczatek + rozmiar]


def suma_wydatkow(transakcje: list[Transakcja]) -> Decimal:
    """Zwraca łączną kwotę wydatków."""
    return sum((t.kwota for t in transakcje if isinstance(t, Wydatek)), ZERO)


def suma_przychodow(transakcje: list[Transakcja]) -> Decimal:
    """Zwraca łączną kwotę przychodów."""
    return sum((t.kwota for t in transakcje if isinstance(t, Przychod)), ZERO)


def bilans(transakcje: list[Transakcja]) -> Decimal:
    """Zwraca różnicę przychodów i wydatków."""
    return sum((t.wplyw for t in transakcje), ZERO)
