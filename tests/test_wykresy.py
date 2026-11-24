"""Testy wykresów i historii salda."""

import sys
from datetime import date
from decimal import Decimal

import pytest

from skarbonka.services import analizy, wykresy
from skarbonka.wyjatki import BladPliku, BrakBiblioteki

LISTOPAD = date(2026, 11, 1)
KWOTY = {"Mieszkanie": Decimal("300"), "Jedzenie": Decimal("120.50")}
NAGLOWEK_PNG = b"\x89PNG"


def test_wszystkie_wykresy_powstaja(transakcje, tmp_path):
    historia = analizy.historia_salda(transakcje, Decimal("100"), date(2026, 11, 24))
    wykresy.wykres_kategorii(KWOTY, LISTOPAD, tmp_path / "nowy" / "a.png")
    wykresy.wykres_trendu(analizy.trend(transakcje, LISTOPAD), tmp_path / "nowy" / "b.png")
    wykresy.wykres_salda(historia, tmp_path / "nowy" / "c.png")
    pliki = sorted((tmp_path / "nowy").iterdir())
    assert len(pliki) == 3
    assert all(plik.read_bytes().startswith(NAGLOWEK_PNG) for plik in pliki)


def test_nie_mozna_zapisac(tmp_path):
    przeszkoda = tmp_path / "plik"
    przeszkoda.write_text("", encoding="utf-8")
    with pytest.raises(BladPliku):
        wykresy.wykres_kategorii(KWOTY, LISTOPAD, przeszkoda / "a.png")


def test_brak_matplotlib(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "matplotlib.figure", None)
    with pytest.raises(BrakBiblioteki):
        wykresy.wykres_kategorii(KWOTY, LISTOPAD, tmp_path / "a.png")


def test_historia_salda(transakcje):
    wynik = dict(analizy.historia_salda(transakcje, Decimal("5000"), date(2026, 11, 12), dni=13))
    assert len(wynik) == 14
    assert wynik[date(2026, 11, 12)] == Decimal("5000")
    assert wynik[date(2026, 11, 9)] == Decimal("5100")
    assert wynik[date(2026, 11, 4)] == Decimal("5400")
    assert wynik[date(2026, 10, 31)] == Decimal("400")
    assert wynik[date(2026, 10, 30)] == Decimal("420")
