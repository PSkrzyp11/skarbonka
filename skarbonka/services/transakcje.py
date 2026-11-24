"""Obliczenia na transakcjach."""

from decimal import Decimal

from skarbonka.models.transakcja import ZERO, Przychod, Transakcja, Wydatek


def od_najnowszych(transakcje: list[Transakcja]) -> list[Transakcja]:
    """Zwraca nową listę posortowaną od najnowszej transakcji."""
    return sorted(transakcje, key=lambda t: (t.data, t.id), reverse=True)


def suma_wydatkow(transakcje: list[Transakcja]) -> Decimal:
    """Zwraca łączną kwotę wydatków."""
    return sum((t.kwota for t in transakcje if isinstance(t, Wydatek)), ZERO)


def suma_przychodow(transakcje: list[Transakcja]) -> Decimal:
    """Zwraca łączną kwotę przychodów."""
    return sum((t.kwota for t in transakcje if isinstance(t, Przychod)), ZERO)


def bilans(transakcje: list[Transakcja]) -> Decimal:
    """Zwraca różnicę przychodów i wydatków."""
    return sum((t.wplyw for t in transakcje), ZERO)
