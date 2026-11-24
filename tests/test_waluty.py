"""Testy kursów walut. Nie łączą się z internetem."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from http.client import IncompleteRead
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from skarbonka.models.kurs import Kurs
from skarbonka.services import waluty
from skarbonka.services.waluty import SerwisWalut
from skarbonka.storage.repozytoria_planu import RepozytoriumKursow
from skarbonka.utils.walidacja import parsuj_kurs
from skarbonka.wyjatki import BladKursu, BladWalidacji, BrakKursu

PIATEK = date(2026, 11, 20)
NIEDZIELA = date(2026, 11, 22)


@pytest.fixture
def nbp(monkeypatch):
    """Zwraca funkcję, która ustawia treść odpowiedzi NBP albo błąd."""

    def ustaw(odpowiedz: bytes | Exception) -> None:
        def podstawiony_urlopen(adres, timeout):
            if isinstance(odpowiedz, Exception):
                raise odpowiedz
            return BytesIO(odpowiedz)

        monkeypatch.setattr(waluty, "urlopen", podstawiony_urlopen)

    return ustaw


def blad_http(kod: int) -> HTTPError:
    return HTTPError("https://api.nbp.pl", kod, "", None, None)


def test_kurs_z_odpowiedzi(nbp):
    nbp(b'{"rates": [{"mid": 4.2512}]}')
    assert waluty.pobierz_z_nbp("EUR", PIATEK) == Decimal("4.2512")


def test_dzien_bez_kursu(nbp):
    nbp(blad_http(404))
    with pytest.raises(BrakKursu):
        waluty.pobierz_z_nbp("EUR", NIEDZIELA)


@pytest.mark.parametrize(
    "odpowiedz",
    [
        URLError("brak internetu"),
        TimeoutError(),
        ConnectionResetError(),
        IncompleteRead(b""),
        blad_http(500),
        b"to nie JSON",
        b"\xff\xff",
        b"{}",
        b'{"rates": []}',
        b'{"rates": [{"mid": "abc"}]}',
        b"[1]",
    ],
)
def test_problemy_z_nbp(nbp, odpowiedz):
    nbp(odpowiedz)
    with pytest.raises(BladKursu) as blad:
        waluty.pobierz_z_nbp("EUR", PIATEK)
    assert not isinstance(blad.value, BrakKursu)


@pytest.fixture
def kursy(baza) -> RepozytoriumKursow:
    return RepozytoriumKursow(baza)


def test_weekend_cofa_sie_do_piatku_i_zapamietuje(kursy):
    zapytania = []

    def pobierz(waluta, dzien):
        zapytania.append(dzien)
        if dzien > PIATEK:
            raise BrakKursu("weekend")
        return Decimal("4.25")

    serwis = SerwisWalut(kursy, pobierz)
    assert serwis.kurs("EUR", NIEDZIELA) == Kurs("EUR", PIATEK, Decimal("4.25"), 1)
    assert len(zapytania) == 3
    assert serwis.kurs("EUR", PIATEK).wartosc == Decimal("4.25")
    assert len(zapytania) == 3


def test_bez_internetu_uzywa_zapisanego(kursy):
    def brak_internetu(waluta, dzien):
        raise BladKursu("brak połączenia")

    serwis = SerwisWalut(kursy, brak_internetu)
    with pytest.raises(BladKursu):
        serwis.kurs("EUR", NIEDZIELA)
    kursy.dodaj(Kurs("USD", PIATEK, Decimal("3.9")))
    kursy.dodaj(Kurs("EUR", date(2026, 11, 1), Decimal("4.1")))
    with pytest.raises(BladKursu):
        serwis.kurs("EUR", NIEDZIELA)
    kursy.dodaj(Kurs("EUR", PIATEK, Decimal("4.2")))
    assert serwis.kurs("EUR", NIEDZIELA).wartosc == Decimal("4.2")


def test_tydzien_bez_kursu(kursy):
    def pobierz(waluta, dzien):
        raise BrakKursu("brak")

    with pytest.raises(BladKursu):
        SerwisWalut(kursy, pobierz).kurs("EUR", NIEDZIELA)


@pytest.mark.parametrize("wartosc", ["0", "-1", "NaN", "Infinity"])
def test_niepoprawny_kurs(wartosc):
    with pytest.raises(BladKursu):
        Kurs("EUR", PIATEK, Decimal(wartosc))


def test_przeliczanie():
    assert Kurs("EUR", PIATEK, Decimal("4.2512")).przelicz(Decimal("12.50")) == Decimal("53.14")


def test_parsowanie_kursu():
    assert parsuj_kurs("4,2512") == Decimal("4.2512")
    for tekst in ("", "0", "-1", "abc", "1 000", "1e5"):
        with pytest.raises(BladWalidacji):
            parsuj_kurs(tekst)


def test_transakcja_pamieta_walute(serwisy, transakcje):
    obca = replace(transakcje[0], waluta="EUR", kwota_oryg=Decimal("4.70"))
    serwisy.transakcje.zmien(obca)
    assert serwisy.transakcje.pobierz(1) == obca
    assert "4,70 EUR" in obca.opis_z_waluta
    assert transakcje[1].opis_z_waluta == "Pensja"
