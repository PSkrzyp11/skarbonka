"""Testy wczytywania danych i menu z podstawionym input()."""

from datetime import date
from decimal import Decimal

import pytest

from skarbonka.services.zestaw import dodaj_dane_startowe, utworz_serwisy
from skarbonka.ui import wejscie
from skarbonka.ui.aplikacja import Aplikacja
from skarbonka.ui.menu import Menu, OpcjaMenu
from skarbonka.wyjatki import AnulowanoOperacje, BladSkarbonki, NieZnalezionoRekordu


def test_kwota_pyta_do_skutku(odpowiedzi):
    odpowiedzi("abc", "", "-5", "12,50")
    assert wejscie.wczytaj_kwote() == Decimal("12.50")


def test_enter_wstawia_wartosc_domyslna(odpowiedzi):
    odpowiedzi("", "")
    assert wejscie.wczytaj_date() == date.today()
    assert wejscie.wczytaj_kwote(domyslna=Decimal("7")) == Decimal("7")


def test_anulowanie(odpowiedzi):
    odpowiedzi(" ANULUJ ")
    with pytest.raises(AnulowanoOperacje):
        wejscie.wczytaj_tekst("Opis")


def test_wybor_z_listy(odpowiedzi):
    odpowiedzi("0", "4", "2")
    assert wejscie.wybierz("Litera", ["a", "b", "c"]) == "b"


def test_wybor_jedynego_i_z_pustej_listy():
    assert wejscie.wybierz("Litera", ["a"]) == "a"
    with pytest.raises(NieZnalezionoRekordu):
        wejscie.wybierz("Litera", [])


def test_wybor_wszystkich(odpowiedzi):
    odpowiedzi("", "1")
    assert wejscie.wybierz_lub_wszystkie("Litera", ["a"]) is None
    assert wejscie.wybierz_lub_wszystkie("Litera", ["a"]) == "a"


def test_menu_przezywa_blad_opcji(odpowiedzi, capsys):
    def zepsuta_opcja():
        raise BladSkarbonki("coś poszło nie tak")

    odpowiedzi("9", "1", "0")
    Menu("Test", [OpcjaMenu("Zepsuta", zepsuta_opcja)]).uruchom()
    assert "coś poszło nie tak" in capsys.readouterr().out


def test_menu_przezywa_nieoczekiwany_blad(odpowiedzi, capsys, caplog):
    odpowiedzi("1", "0")
    Menu("Test", [OpcjaMenu("Dzielenie", lambda: 1 / 0)]).uruchom()
    assert "Nieoczekiwany błąd" in capsys.readouterr().out
    assert "ZeroDivisionError" in caplog.text


def test_koniec_danych_przerywa_menu(odpowiedzi):
    odpowiedzi()
    with pytest.raises(EOFError):
        Menu("Test", []).uruchom()


def test_dodanie_wydatku_przez_menu(odpowiedzi, baza):
    serwisy = utworz_serwisy(baza)
    dodaj_dane_startowe(serwisy)
    odpowiedzi("1", "1", "20", "", "Kawa", "1", "0", "0")
    Aplikacja(serwisy).uruchom()
    transakcje = serwisy.transakcje.wszystkie()
    assert [t.kwota for t in transakcje] == [Decimal("20")]
