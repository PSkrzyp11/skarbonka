"""Testy transakcji, formatowania i dat."""

from datetime import date
from decimal import Decimal

import pytest

from skarbonka.models.transakcja import Przelew, Przychod, Transakcja, Wydatek
from skarbonka.utils.daty import przesun_miesiac
from skarbonka.utils.formatowanie import formatuj_kwote, formatuj_miesiac, formatuj_procent
from skarbonka.wyjatki import BladWalidacji, NieprawidlowaKwota

DZIEN = date(2026, 11, 24)
KWOTA = Decimal("50.00")


def test_wplyw_na_saldo():
    assert Wydatek(DZIEN, KWOTA, "x", 1).wplyw == -KWOTA
    assert Przychod(DZIEN, KWOTA, "x", 1).wplyw == KWOTA


def test_wydatek_nie_rusza_innego_konta():
    assert Wydatek(DZIEN, KWOTA, "x", 1).wplyw_na_konto(2) == 0


def test_przelew_przesuwa_pieniadze():
    przelew = Przelew(DZIEN, KWOTA, "x", 1, konto_docelowe_id=2)
    assert przelew.wplyw == 0
    assert [przelew.wplyw_na_konto(nr) for nr in (1, 2, 3)] == [-KWOTA, KWOTA, 0]
    assert przelew.dotyczy_konta(2)
    assert not przelew.dotyczy_konta(3)


def test_przelew_na_to_samo_konto():
    with pytest.raises(BladWalidacji):
        Przelew(DZIEN, KWOTA, "x", 1, konto_docelowe_id=1)


@pytest.mark.parametrize("kwota", ["0", "-1"])
def test_kwota_musi_byc_dodatnia(kwota):
    with pytest.raises(NieprawidlowaKwota):
        Wydatek(DZIEN, Decimal(kwota), "x", 1)


def test_nie_mozna_utworzyc_klasy_abstrakcyjnej():
    with pytest.raises(TypeError):
        Transakcja(DZIEN, KWOTA, "x", 1)


def test_porownywanie():
    assert Wydatek(DZIEN, KWOTA, "x", 1) == Wydatek(DZIEN, Decimal("50"), "x", 1)
    assert Wydatek(DZIEN, KWOTA, "x", 1) != Przychod(DZIEN, KWOTA, "x", 1)


def test_tekst_transakcji():
    tekst = str(Wydatek(DZIEN, Decimal("1234.5"), "Czynsz", 1, id=7))
    assert "24.11.2026" in tekst
    assert "-1 234,50 zł" in tekst
    assert "Czynsz" in tekst


def test_formatowanie():
    assert formatuj_kwote(Decimal("-1234567.8")) == "-1 234 567,80 zł"
    assert formatuj_miesiac(DZIEN) == "listopad 2026"
    assert formatuj_procent(84.46) == "84,5%"


@pytest.mark.parametrize(
    ("dzien", "ile", "wynik"),
    [
        (date(2026, 1, 31), 1, date(2026, 2, 28)),
        (date(2028, 1, 31), 1, date(2028, 2, 29)),
        (date(2026, 12, 15), 1, date(2027, 1, 15)),
        (date(2026, 1, 1), -1, date(2025, 12, 1)),
        (date(2026, 11, 1), -23, date(2024, 12, 1)),
    ],
)
def test_przesuwanie_miesiaca(dzien, ile, wynik):
    assert przesun_miesiac(dzien, ile) == wynik
