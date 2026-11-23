"""Obliczenia na transakcjach."""

from decimal import Decimal

from skarbonka.models.transakcja import Przychod, Transakcja, Wydatek
from skarbonka.wyjatki import NieZnalezionoRekordu

ZERO = Decimal("0.00")


def dodaj(transakcje: list[Transakcja], nowa: Transakcja) -> None:
    """Nadaje transakcji kolejny numer i dopisuje ją do listy."""
    nowa.id = max((t.id for t in transakcje), default=0) + 1
    transakcje.append(nowa)


def znajdz(transakcje: list[Transakcja], numer: int) -> Transakcja:
    """Zwraca transakcję o podanym numerze."""
    for transakcja in transakcje:
        if transakcja.id == numer:
            return transakcja
    raise NieZnalezionoRekordu(f"Nie ma transakcji o numerze {numer}.")


def usun(transakcje: list[Transakcja], numer: int) -> None:
    """Usuwa transakcję o podanym numerze."""
    transakcje.remove(znajdz(transakcje, numer))


def od_najnowszych(transakcje: list[Transakcja]) -> list[Transakcja]:
    """Zwraca nową listę posortowaną od najnowszej transakcji."""
    return sorted(transakcje, key=lambda t: (t.data, t.id), reverse=True)


def suma_wydatkow(transakcje: list[Transakcja]) -> Decimal:
    """Zwraca łączną kwotę wydatków."""
    return sum((t.kwota for t in transakcje if isinstance(t, Wydatek)), ZERO)


def suma_przychodow(transakcje: list[Transakcja]) -> Decimal:
    """Zwraca łączną kwotę przychodów."""
    return sum((t.kwota for t in transakcje if isinstance(t, Przychod)), ZERO)


def saldo(transakcje: list[Transakcja]) -> Decimal:
    """Zwraca sumę wpływów wszystkich transakcji na saldo."""
    return sum((t.wplyw for t in transakcje), ZERO)
