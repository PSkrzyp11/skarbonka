"""Testy importu wyciągu i eksportu transakcji."""

from datetime import date
from decimal import Decimal

import pytest

from skarbonka.config import KATALOG_PROJEKTU
from skarbonka.models.transakcja import Przychod, Wydatek
from skarbonka.services.profile import PROFIL_SKARBONKI
from skarbonka.wyjatki import BladBazy, NieZnalezionoRekordu

PRZYKLADY = KATALOG_PROJEKTU / "przyklady"


@pytest.fixture
def przygotuj(serwisy, tmp_path):
    """Zwraca funkcję, która przygotowuje import podanych linii."""

    def wykonaj(*linie: str):
        sciezka = tmp_path / "wyciag.csv"
        sciezka.write_text("\n".join(("data;kwota;opis;kategoria", *linie)), encoding="utf-8")
        return serwisy.importer.przygotuj(sciezka, PROFIL_SKARBONKI, 1)

    return wykonaj


def test_znak_kwoty_wyznacza_rodzaj(przygotuj):
    podglad = przygotuj("2026-11-01;-10,50;Zakupy;jedzenie", "02.11.2026;+100;Zwrot;")
    assert podglad.nowe == [
        Wydatek(date(2026, 11, 1), Decimal("10.50"), "Zakupy", 1, 1),
        Przychod(date(2026, 11, 2), Decimal("100"), "Zwrot", 1, 3),
    ]


def test_opis_jest_czyszczony(przygotuj):
    opisy = ("x" * 100, "a\tb   c", "")
    podglad = przygotuj(*(f"2026-11-01;-1;{opis};" for opis in opisy))
    assert [t.opis for t in podglad.nowe] == ["x" * 60, "a b c", "Import"]


@pytest.mark.parametrize(
    "linia",
    [
        "31.02.2026;-10;x;",
        "2099-01-01;-10;x;",
        ";-10;x;",
        "2026-11-01;;x;",
        "2026-11-01;0,00;x;",
        "2026-11-01;-10 EUR;x;",
        "2026-11-01",
    ],
)
def test_bledne_linie_nie_przerywaja_importu(przygotuj, linia):
    podglad = przygotuj(linia, "2026-11-01;-10;poprawna;")
    assert len(podglad.nowe) == 1
    assert podglad.bledy[0].startswith("Linia 2:")


def test_duplikaty(serwisy, przygotuj):
    linie = ("2026-11-01;-10;Kawa;", "2026-11-01;-10;Kawa;")
    pierwszy = przygotuj(*linie)
    assert len(pierwszy.nowe) == 2
    serwisy.importer.zapisz(pierwszy.plik, pierwszy.nowe)

    drugi = przygotuj("2026-11-01;-10,00;KAWA;", "2026-11-01;-11;Kawa;")
    assert len(drugi.duplikaty) == 1
    assert len(drugi.nowe) == 1


def test_cofniecie_importu(serwisy, przygotuj, transakcje):
    podglad = przygotuj("2026-11-01;-10;Kawa;", "2026-11-02;-10;Kawa;")
    serwisy.importer.zapisz(podglad.plik, podglad.nowe)
    assert len(serwisy.transakcje.wszystkie()) == len(transakcje) + 2

    assert serwisy.importer.cofnij(serwisy.importer.ostatni()) == 2
    assert serwisy.transakcje.wszystkie() == transakcje
    with pytest.raises(NieZnalezionoRekordu):
        serwisy.importer.ostatni()


def test_import_zapisuje_wszystko_albo_nic(serwisy, przygotuj, transakcje):
    podglad = przygotuj("2026-11-01;-10;Kawa;", "2026-11-02;-10;Kawa;")
    podglad.nowe[1].konto_id = 99
    with pytest.raises(BladBazy):
        serwisy.importer.zapisz(podglad.plik, podglad.nowe)
    assert serwisy.transakcje.wszystkie() == transakcje
    with pytest.raises(NieZnalezionoRekordu):
        serwisy.importer.ostatni()


def test_pliki_przykladowe(serwisy):
    poprawny = serwisy.importer.przygotuj(PRZYKLADY / "wyciag_demo.csv", PROFIL_SKARBONKI, 1)
    assert (len(poprawny.nowe), len(poprawny.bledy)) == (8, 0)
    uszkodzony = serwisy.importer.przygotuj(
        PRZYKLADY / "wyciag_uszkodzony.csv", PROFIL_SKARBONKI, 1
    )
    assert (len(uszkodzony.nowe), len(uszkodzony.bledy)) == (2, 6)


def test_eksport_mozna_zaimportowac(serwisy, transakcje, tmp_path):
    sciezka = tmp_path / "eksport.csv"
    serwisy.eksporter.zapisz(transakcje, sciezka)
    for konto_id, duplikaty in ((1, [1, 4]), (2, [2, 3])):
        podglad = serwisy.importer.przygotuj(sciezka, PROFIL_SKARBONKI, konto_id)
        znane = {t.odcisk for t in transakcje if t.id in duplikaty}
        assert {t.odcisk for t in podglad.duplikaty} == znane
        assert len(podglad.bledy) == 1
        assert "przelew" in podglad.bledy[0]


def test_tresc_eksportu(serwisy, transakcje, tmp_path):
    sciezka = tmp_path / "eksport.csv"
    serwisy.eksporter.zapisz(transakcje, sciezka)
    linie = sciezka.read_text(encoding="utf-8-sig").splitlines()
    assert linie[0] == "data;rodzaj;kwota;opis;konto;konto docelowe;kategoria"
    assert linie[1] == "2026-10-31;wydatek;-20,00;Kawa czarna;Portfel;;Jedzenie"
    assert linie[5] == "2026-11-12;przelew;1000,00;ROR -> Portfel;ROR;Portfel;"
