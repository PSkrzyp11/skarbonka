"""Testy reguł kategoryzacji."""

from datetime import date
from decimal import Decimal

import pytest

from skarbonka.models.kategoria import Regula
from skarbonka.models.transakcja import Przelew, Przychod, Wydatek
from skarbonka.services.profile import PROFIL_SKARBONKI
from skarbonka.wyjatki import BladWalidacji, RekordWUzyciu

DZIEN = date(2026, 11, 1)


def test_fraza_bez_wzgledu_na_wielkosc_liter():
    assert Regula("biedronka", 1).pasuje("Zakupy BIEDRONKA 123")
    assert not Regula("biedronka", 1).pasuje("Lidl")


def test_wygrywa_priorytet_potem_dluzsza_fraza(serwisy, kategorie):
    jedzenie, mieszkanie, _, rozrywka = kategorie
    serwisy.kategoryzator.dodaj("kino", rozrywka)
    serwisy.kategoryzator.dodaj("kino bar", jedzenie)
    assert serwisy.kategoryzator.dopasuj("Kino Bar Centrum", Wydatek) == jedzenie
    serwisy.kategoryzator.dodaj("bar", mieszkanie, priorytet=5)
    assert serwisy.kategoryzator.dopasuj("Kino Bar Centrum", Wydatek) == mieszkanie


def test_kategoria_musi_pasowac_do_rodzaju(serwisy, kategorie):
    serwisy.kategoryzator.dodaj("firma", kategorie[2])
    assert serwisy.kategoryzator.dopasuj("Firma X", Przychod) == kategorie[2]
    assert serwisy.kategoryzator.dopasuj("Firma X", Wydatek) is None
    assert serwisy.kategoryzator.dopasuj("Firma X", Przelew) is None


def test_powtorzona_fraza(serwisy, kategorie):
    serwisy.kategoryzator.dodaj("firma", kategorie[0])
    serwisy.kategoryzator.dodaj("firma", kategorie[2])
    with pytest.raises(BladWalidacji):
        serwisy.kategoryzator.dodaj("FIRMA", kategorie[1])


def test_regula_chroni_kategorie(serwisy, kategorie):
    regula = serwisy.kategoryzator.dodaj("kino", kategorie[3])
    with pytest.raises(RekordWUzyciu):
        serwisy.kategorie.usun(kategorie[3])
    serwisy.kategoryzator.usun(regula)
    serwisy.kategorie.usun(kategorie[3])


def test_zastosowanie_zmienia_tylko_kategorie_inne(serwisy, kategorie):
    inne = serwisy.kategorie.dodaj("Inne wydatki")
    for opis, kategoria in (("Kino", inne), ("Teatr", inne), ("Kino", kategorie[0])):
        serwisy.transakcje.dodaj(Wydatek(DZIEN, Decimal("1"), opis, 1, kategoria.id))
    serwisy.kategoryzator.dodaj("kino", kategorie[3])
    assert serwisy.kategoryzator.zastosuj() == 1
    wynik = [t.kategoria_id for t in serwisy.transakcje.wszystkie()[-3:]]
    assert wynik == [kategorie[3].id, inne.id, kategorie[0].id]


def test_import_korzysta_z_regul(serwisy, kategorie, tmp_path):
    serwisy.kategoryzator.dodaj("kino", kategorie[3])
    plik = tmp_path / "wyciag.csv"
    plik.write_text(
        "data;kwota;opis;kategoria\n2026-11-01;-1;Kino;\n2026-11-01;-1;Kino;Mieszkanie\n",
        encoding="utf-8",
    )
    nowe = serwisy.importer.przygotuj(plik, PROFIL_SKARBONKI, 1).nowe
    assert [t.kategoria_id for t in nowe] == [kategorie[3].id, kategorie[1].id]
