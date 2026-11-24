"""Testy zapisu obiektów do bazy i odczytu z niej."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from skarbonka.models.kategoria import Kategoria
from skarbonka.models.transakcja import Wydatek
from skarbonka.storage.repozytoria import RepozytoriumKategorii, na_grosze, z_groszy
from skarbonka.wyjatki import BladBazy, NieZnalezionoRekordu


@pytest.fixture
def repozytorium(baza) -> RepozytoriumKategorii:
    wynik = RepozytoriumKategorii(baza)
    wynik.dodaj(Kategoria("Jedzenie"))
    wynik.dodaj(Kategoria("Transport", czy_wydatek=False))
    return wynik


@pytest.mark.parametrize(
    ("kwota", "grosze"),
    [("45.90", 4590), ("0.01", 1), ("-100.5", -10050), ("999999999.99", 99999999999)],
)
def test_grosze(kwota, grosze):
    assert na_grosze(Decimal(kwota)) == grosze
    assert z_groszy(grosze) == Decimal(kwota)


def test_zaokraglanie_do_grosza():
    assert na_grosze(Decimal("1.005")) == 101


def test_dodawanie_nadaje_numery(repozytorium):
    assert [k.id for k in repozytorium.wszystkie()] == [1, 2]
    assert len(repozytorium) == 2


def test_numer_usunietego_nie_wraca(repozytorium):
    repozytorium.usun(2)
    assert repozytorium.dodaj(Kategoria("Zdrowie")).id == 3


def test_zmiana(repozytorium):
    repozytorium.zmien(Kategoria("Auto", id=2))
    assert repozytorium.pobierz(2) == Kategoria("Auto", True, 2)


@pytest.mark.parametrize("operacja", ["pobierz", "usun"])
def test_brak_rekordu(repozytorium, operacja):
    with pytest.raises(NieZnalezionoRekordu):
        getattr(repozytorium, operacja)(99)


def test_zmiana_nieistniejacego(repozytorium):
    with pytest.raises(NieZnalezionoRekordu):
        repozytorium.zmien(Kategoria("X", id=99))


def test_dane_wracaja_bez_zmian(serwisy, konta, kategorie, transakcje):
    assert serwisy.konta.wszystkie() == konta
    assert serwisy.kategorie.wszystkie() == kategorie
    assert serwisy.transakcje.wszystkie() == transakcje


def test_zmiana_przelewu(serwisy, transakcje):
    nowy = replace(transakcje[4], kwota=Decimal("12.34"))
    serwisy.transakcje.zmien(nowy)
    assert serwisy.transakcje.pobierz(5) == nowy


def test_cudzyslow_w_opisie(serwisy):
    opis = "x'); DROP TABLE transakcje; --"
    dodana = serwisy.transakcje.dodaj(Wydatek(date(2026, 11, 1), Decimal("1"), opis, 1, 1))
    assert serwisy.transakcje.pobierz(dodana.id).opis == opis


@pytest.mark.parametrize(
    "zmiana",
    ["data = 'kiedyś'", "grosze = 'dużo'", "rodzaj = 'przelew', konto_docelowe_id = 1"],
)
def test_bledne_dane_w_bazie(baza, serwisy, zmiana):
    baza.wykonaj(f"UPDATE transakcje SET {zmiana} WHERE id = 1")
    with pytest.raises(BladBazy):
        serwisy.transakcje.wszystkie()
