"""Obliczenia na transakcjach."""

from decimal import Decimal

from skarbonka.models.transakcja import Przychod, Transakcja, Wydatek

ZERO = Decimal("0.00")


def suma_wydatkow(transakcje: list[Transakcja]) -> Decimal:
    """Zwraca łączną kwotę wydatków."""
    return sum((t.kwota for t in transakcje if isinstance(t, Wydatek)), ZERO)


def suma_przychodow(transakcje: list[Transakcja]) -> Decimal:
    """Zwraca łączną kwotę przychodów."""
    return sum((t.kwota for t in transakcje if isinstance(t, Przychod)), ZERO)


def saldo(transakcje: list[Transakcja]) -> Decimal:
    """Zwraca sumę wpływów wszystkich transakcji na saldo."""
    return sum((t.wplyw for t in transakcje), ZERO)
