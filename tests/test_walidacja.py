"""Testy zamiany tekstu na wartości."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from skarbonka.utils.walidacja import (
    parsuj_date,
    parsuj_kwote,
    parsuj_miesiac,
    parsuj_numer,
    parsuj_tak_nie,
    parsuj_wybor,
    sprawdz_tekst,
)
from skarbonka.wyjatki import BladWalidacji, NieprawidlowaData, NieprawidlowaKwota


@pytest.mark.parametrize(
    ("tekst", "oczekiwana"),
    [
        ("45", "45"),
        ("45,90", "45.90"),
        (" 45.9 ", "45.9"),
        ("1 234,50", "1234.50"),
        ("1 234,50 zł", "1234.50"),
        ("10 PLN", "10"),
    ],
)
def test_poprawna_kwota(tekst, oczekiwana):
    assert parsuj_kwote(tekst) == Decimal(oczekiwana)


@pytest.mark.parametrize(
    "tekst",
    ["", "   ", "zł", "abc", "0", "-5", "12 50", "1,234", "1e5", "NaN", "1_000", "9999999999"],
)
def test_bledna_kwota(tekst):
    with pytest.raises(NieprawidlowaKwota):
        parsuj_kwote(tekst)


def test_kwota_ujemna_bez_minimum():
    assert parsuj_kwote("−100,50", minimum=None) == Decimal("-100.50")


@pytest.mark.parametrize("tekst", ["24.11.2026", "2026-11-24", "24-11-2026", "24/11/2026"])
def test_formaty_daty(tekst):
    assert parsuj_date(tekst) == date(2026, 11, 24)


def test_slowne_daty():
    assert parsuj_date("Dziś") == date.today()
    assert parsuj_date("wczoraj") == date.today() - timedelta(days=1)


@pytest.mark.parametrize("tekst", ["", "abc", "31.02.2026", "29.02.2025", "01.01.1999"])
def test_bledna_data(tekst):
    with pytest.raises(NieprawidlowaData):
        parsuj_date(tekst)


def test_rok_przestepny():
    assert parsuj_date("29.02.2024") == date(2024, 2, 29)


def test_data_domyslna_i_limit():
    assert parsuj_date("", domyslna=date(2026, 1, 1)) == date(2026, 1, 1)
    with pytest.raises(NieprawidlowaData):
        parsuj_date("02.01.2026", najpozniej=date(2026, 1, 1))


def test_miesiac():
    assert parsuj_miesiac("11.2026") == parsuj_miesiac("2026-11") == date(2026, 11, 1)
    with pytest.raises(NieprawidlowaData):
        parsuj_miesiac("13.2026")


def test_tekst():
    assert sprawdz_tekst("  ala   ma  kota ") == "ala ma kota"
    assert sprawdz_tekst("", puste_ok=True) == ""


@pytest.mark.parametrize("tekst", ["", "   ", "x" * 61, "a\x1bb"])
def test_bledny_tekst(tekst):
    with pytest.raises(BladWalidacji):
        sprawdz_tekst(tekst)


def test_numer():
    assert parsuj_numer(" 12 ") == 12


@pytest.mark.parametrize("tekst", ["", "0", "-1", "1.5", "abc", "²", "1" * 10])
def test_bledny_numer(tekst):
    with pytest.raises(BladWalidacji):
        parsuj_numer(tekst)


def test_tak_nie():
    assert parsuj_tak_nie("T") is True
    assert parsuj_tak_nie("nie") is False
    with pytest.raises(BladWalidacji):
        parsuj_tak_nie("może")


def test_wybor():
    assert parsuj_wybor(" W ", ("w", "p")) == "w"
    with pytest.raises(BladWalidacji):
        parsuj_wybor("x", ("w", "p"))
