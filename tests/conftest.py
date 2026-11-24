"""Dane wspólne dla wielu testów."""

from datetime import date
from decimal import Decimal

import pytest

from skarbonka.models.enums import TypKonta
from skarbonka.models.kategoria import Kategoria
from skarbonka.models.konto import Konto
from skarbonka.models.transakcja import Przelew, Przychod, Transakcja, Wydatek


@pytest.fixture
def konta() -> list[Konto]:
    return [
        Konto("Portfel", TypKonta.GOTOWKA, Decimal("100.00"), id=1),
        Konto("ROR", TypKonta.BIEZACE, Decimal("-50.00"), id=2),
        Konto("Lokata", TypKonta.OSZCZEDNOSCI, id=3),
    ]


@pytest.fixture
def kategorie() -> list[Kategoria]:
    return [
        Kategoria("Jedzenie", id=1),
        Kategoria("Mieszkanie", id=2),
        Kategoria("Wynagrodzenie", czy_wydatek=False, id=3),
        Kategoria("Rozrywka", id=4),
    ]


@pytest.fixture
def transakcje() -> list[Transakcja]:
    return [
        Wydatek(date(2026, 10, 31), Decimal("20.00"), "Kawa czarna", 1, 1, id=1),
        Przychod(date(2026, 11, 1), Decimal("5000.00"), "Pensja", 2, 3, id=2),
        Wydatek(date(2026, 11, 5), Decimal("300.00"), "Czynsz", 2, 2, id=3),
        Wydatek(date(2026, 11, 10), Decimal("100.00"), "KAWA i obiad", 1, 1, id=4),
        Przelew(
            date(2026, 11, 12), Decimal("1000.00"), "ROR -> Portfel", 2, id=5, konto_docelowe_id=1
        ),
    ]
