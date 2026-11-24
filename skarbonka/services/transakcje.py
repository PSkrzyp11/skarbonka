"""Filtrowanie, sortowanie i sumowanie transakcji."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal

from skarbonka.models.transakcja import ZERO, Przychod, Transakcja, Wydatek
from skarbonka.wyjatki import BladWalidacji

SORTOWANIA: dict[str, tuple[Callable[[Transakcja], tuple], bool]] = {
    "od najnowszych": (lambda t: (t.data, t.id), True),
    "od najstarszych": (lambda t: (t.data, t.id), False),
    "od największych kwot": (lambda t: (t.kwota, t.id), True),
    "od najmniejszych kwot": (lambda t: (t.kwota, t.id), False),
}


def posortuj(transakcje: list[Transakcja], sposob: str = "od najnowszych") -> list[Transakcja]:
    """Zwraca nową listę posortowaną wybranym sposobem."""
    klucz, malejaco = SORTOWANIA[sposob]
    return sorted(transakcje, key=klucz, reverse=malejaco)


def filtruj(
    transakcje: list[Transakcja],
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
    return [t for t in transakcje if all(warunek(t) for warunek in warunki)]


def suma_wydatkow(transakcje: list[Transakcja]) -> Decimal:
    """Zwraca łączną kwotę wydatków."""
    return sum((t.kwota for t in transakcje if isinstance(t, Wydatek)), ZERO)


def suma_przychodow(transakcje: list[Transakcja]) -> Decimal:
    """Zwraca łączną kwotę przychodów."""
    return sum((t.kwota for t in transakcje if isinstance(t, Przychod)), ZERO)


def bilans(transakcje: list[Transakcja]) -> Decimal:
    """Zwraca różnicę przychodów i wydatków."""
    return sum((t.wplyw for t in transakcje), ZERO)
