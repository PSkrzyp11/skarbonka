"""Testy prognozy salda."""

from datetime import date
from decimal import Decimal

import pytest

from skarbonka.models.cykliczna import Cykliczna
from skarbonka.models.enums import Czestotliwosc, TypKonta
from skarbonka.models.transakcja import Wydatek
from skarbonka.services.zestaw import utworz_serwisy
from skarbonka.wyjatki import ZaMaloDanych

DZIS = date(2026, 11, 24)


@pytest.fixture
def puste(baza, tmp_path):
    """Serwisy z jednym kontem (3240 zł) i jedną kategorią."""
    serwisy = utworz_serwisy(baza, tmp_path)
    serwisy.konta.dodaj("ROR", TypKonta.BIEZACE, Decimal("3240"))
    serwisy.kategorie.dodaj("Jedzenie")
    return serwisy


def wydaj(serwisy, data: date, kwota: str) -> None:
    serwisy.transakcje.dodaj(Wydatek(data, Decimal(kwota), "x", 1, 1))


def test_trzy_warianty(puste):
    wydaj(puste, date(2026, 8, 31), "1488")
    wydaj(puste, date(2026, 9, 1), "1845")
    wydaj(puste, date(2026, 10, 15), "2325")
    saldo = Decimal("3240") - Decimal("5658")

    prognoza = puste.prognoza.policz(DZIS)
    assert (prognoza.dni, prognoza.koniec) == (6, date(2026, 11, 30))
    assert (prognoza.tempo_min, prognoza.tempo_srednie, prognoza.tempo_maks) == (
        Decimal("48"),
        Decimal("61.5"),
        Decimal("75"),
    )
    assert prognoza.optymistyczna == saldo - 288
    assert prognoza.realistyczna == saldo - 369
    assert prognoza.pesymistyczna == saldo - 450


def test_cykliczne_sa_liczone_osobno(puste):
    cykliczna = puste.cykliczne.dodaj(
        Cykliczna(
            "Internet",
            "wydatek",
            Decimal("49.99"),
            1,
            1,
            date(2026, 10, 28),
            Czestotliwosc.MIESIAC,
        ),
        DZIS,
    )
    puste.cykliczne.zaksieguj(cykliczna, date(2026, 10, 28))
    prognoza = puste.prognoza.policz(DZIS)
    assert prognoza.tempo_maks == 0
    assert prognoza.cykliczne == Decimal("-49.99")
    assert prognoza.realistyczna == Decimal("3240") - 2 * Decimal("49.99")


def test_pomija_miesiace_bez_historii(puste):
    wydaj(puste, date(2026, 10, 1), "310")
    prognoza = puste.prognoza.policz(DZIS)
    assert prognoza.tempo_min == prognoza.tempo_maks == Decimal("10")


def test_ostatni_dzien_miesiaca(puste):
    wydaj(puste, date(2026, 10, 1), "310")
    prognoza = puste.prognoza.policz(date(2026, 11, 30))
    assert prognoza.dni == 0
    assert prognoza.pesymistyczna == prognoza.optymistyczna == Decimal("2930.00")


def test_styczen_korzysta_z_poprzedniego_roku(puste):
    wydaj(puste, date(2026, 12, 1), "310")
    assert puste.prognoza.policz(date(2027, 1, 10)).tempo_maks == Decimal("10")


def test_za_malo_danych(puste):
    wydaj(puste, date(2026, 11, 1), "310")
    with pytest.raises(ZaMaloDanych):
        puste.prognoza.policz(DZIS)
