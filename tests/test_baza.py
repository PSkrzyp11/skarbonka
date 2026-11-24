"""Testy połączenia z bazą danych."""

import pytest

from skarbonka.storage.baza import Baza
from skarbonka.wyjatki import BladBazy, UszkodzonaBaza


def liczba_kategorii(baza) -> int:
    return len(baza.zapytaj("SELECT id FROM kategorie"))


def test_dane_zostaja_w_pliku(tmp_path):
    plik = tmp_path / "nowy" / "test.db"
    baza = Baza(plik)
    baza.wstaw("kategorie", {"nazwa": "Jedzenie"})
    baza.zamknij()

    ponownie = Baza(plik)
    assert ponownie.zapytaj("SELECT nazwa FROM kategorie")[0]["nazwa"] == "Jedzenie"
    ponownie.zamknij()


def test_bledne_polecenie(baza):
    with pytest.raises(BladBazy):
        baza.wykonaj("TO NIE JEST SQL")


def test_transakcja_wycofuje_wszystko_po_bledzie(baza):
    with pytest.raises(ValueError):
        with baza.transakcja():
            baza.wstaw("kategorie", {"nazwa": "Jedzenie"})
            raise ValueError
    assert liczba_kategorii(baza) == 0


def test_transakcja_zapisuje_calosc(baza):
    with baza.transakcja():
        baza.wstaw("kategorie", {"nazwa": "A"})
        with baza.transakcja():
            baza.wstaw("kategorie", {"nazwa": "B"})
    assert liczba_kategorii(baza) == 2


def test_wewnetrzna_transakcja_jest_czescia_zewnetrznej(baza):
    with pytest.raises(ValueError):
        with baza.transakcja():
            with baza.transakcja():
                baza.wstaw("kategorie", {"nazwa": "A"})
            raise ValueError
    assert liczba_kategorii(baza) == 0


@pytest.mark.parametrize(
    "wiersz",
    [
        {"rodzaj": "inny", "grosze": 100, "konto_id": 1},
        {"rodzaj": "wydatek", "grosze": 0, "konto_id": 1},
        {"rodzaj": "wydatek", "grosze": 100, "konto_id": 99},
    ],
)
def test_baza_odrzuca_bledne_transakcje(baza, wiersz):
    baza.wstaw("konta", {"nazwa": "Portfel", "typ": "gotówka"})
    with pytest.raises(BladBazy):
        baza.wstaw("transakcje", {"data": "2026-11-24", "opis": "x", **wiersz})


def test_uszkodzony_plik(tmp_path):
    plik = tmp_path / "zepsuta.db"
    plik.write_text("to na pewno nie jest baza danych " * 100, encoding="utf-8")
    with pytest.raises(UszkodzonaBaza):
        Baza(plik)
    plik.unlink()


def test_sciezka_jest_katalogiem(tmp_path):
    with pytest.raises(BladBazy) as blad:
        Baza(tmp_path)
    assert not isinstance(blad.value, UszkodzonaBaza)


def test_zamknieta_baza(baza):
    baza.zamknij()
    with pytest.raises(BladBazy):
        baza.wykonaj("SELECT 1")
