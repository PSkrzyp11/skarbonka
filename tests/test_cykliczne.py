"""Testy transakcji cyklicznych i aktualizacji starej bazy."""

import sqlite3
from dataclasses import replace
from datetime import date
from decimal import Decimal
from itertools import islice

import pytest

from skarbonka.models.cykliczna import Cykliczna
from skarbonka.models.enums import Czestotliwosc, StanPlatnosci
from skarbonka.services.cykliczne import do_zaplaty
from skarbonka.storage.baza import Baza
from skarbonka.wyjatki import BladWalidacji, NieprawidlowaData, NieprawidlowaKwota, RekordWUzyciu

DZIS = date(2026, 11, 24)


def czynsz(start=date(2026, 9, 10), czestotliwosc=Czestotliwosc.MIESIAC, **pola) -> Cykliczna:
    dane = {"rodzaj": "wydatek", "kwota": Decimal("100"), "konto_id": 1, "kategoria_id": 2}
    return Cykliczna("Czynsz", start=start, czestotliwosc=czestotliwosc, **(dane | pola))


@pytest.mark.parametrize(
    ("start", "czestotliwosc", "oczekiwane"),
    [
        (
            date(2026, 1, 31),
            Czestotliwosc.MIESIAC,
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)],
        ),
        (
            date(2026, 12, 28),
            Czestotliwosc.TYDZIEN,
            [date(2026, 12, 28), date(2027, 1, 4), date(2027, 1, 11)],
        ),
        (
            date(2026, 11, 30),
            Czestotliwosc.KWARTAL,
            [date(2026, 11, 30), date(2027, 2, 28), date(2027, 5, 30)],
        ),
        (
            date(2024, 2, 29),
            Czestotliwosc.ROK,
            [date(2024, 2, 29), date(2025, 2, 28), date(2026, 2, 28)],
        ),
    ],
)
def test_kolejne_terminy(start, czestotliwosc, oczekiwane):
    terminy = czynsz(start, czestotliwosc).terminy(start, date(2030, 1, 1))
    assert list(islice(terminy, 3)) == oczekiwane


def test_zakres_terminow():
    wynik = list(czynsz().terminy(date(2026, 10, 10), date(2026, 11, 10)))
    assert wynik == [date(2026, 10, 10), date(2026, 11, 10)]
    assert list(czynsz(start=date(2027, 1, 1)).terminy(DZIS, DZIS)) == []


def test_niezaksiegowane_po_ostatnim():
    assert list(czynsz(ostatnia=date(2026, 10, 10)).niezaksiegowane(DZIS)) == [date(2026, 11, 10)]


@pytest.mark.parametrize(
    ("pola", "wyjatek"),
    [({"kwota": Decimal("0")}, NieprawidlowaKwota), ({"rodzaj": "przelew"}, BladWalidacji)],
)
def test_bledne_dane(pola, wyjatek):
    with pytest.raises(wyjatek):
        czynsz(**pola)


@pytest.mark.parametrize(
    ("czestotliwosc", "oczekiwane"),
    [
        (Czestotliwosc.TYDZIEN, "-433.33"),
        (Czestotliwosc.MIESIAC, "-100"),
        (Czestotliwosc.KWARTAL, "-33.33"),
        (Czestotliwosc.ROK, "-8.33"),
    ],
)
def test_kwota_miesieczna(czestotliwosc, oczekiwane):
    assert czynsz(czestotliwosc=czestotliwosc).miesiecznie == Decimal(oczekiwane)


def test_bilans(serwisy):
    pusty = serwisy.cykliczne.bilans()
    assert (pusty.na_czysto, pusty.procent) == (0, None)
    serwisy.cykliczne.dodaj(czynsz(kwota=Decimal("1500")), DZIS)
    assert serwisy.cykliczne.bilans().na_czysto == Decimal("-1500.00")
    pensja = czynsz(kwota=Decimal("6000"), rodzaj="przychód", kategoria_id=3)
    pensja.nazwa = "Pensja"
    serwisy.cykliczne.dodaj(pensja, DZIS)
    wylaczona = czynsz(kwota=Decimal("999"))
    wylaczona.nazwa = "Siłownia"
    serwisy.cykliczne.przelacz(serwisy.cykliczne.dodaj(wylaczona, DZIS))
    bilans = serwisy.cykliczne.bilans()
    assert (bilans.przychody, bilans.wydatki) == (Decimal("6000.00"), Decimal("1500.00"))
    assert (bilans.na_czysto, bilans.procent) == (Decimal("4500.00"), 75.0)
    assert bilans.dziennie == Decimal("150.00")


def test_harmonogram(serwisy):
    serwisy.cykliczne.dodaj(czynsz(start=date(2026, 10, 10), kwota=Decimal("50")), DZIS)
    prad = czynsz(start=date(2026, 11, 30), czestotliwosc=Czestotliwosc.KWARTAL)
    prad.nazwa = "Prąd"
    serwisy.cykliczne.dodaj(prad, DZIS)
    wylaczona = czynsz()
    wylaczona.nazwa = "Siłownia"
    serwisy.cykliczne.przelacz(serwisy.cykliczne.dodaj(wylaczona, DZIS))
    platnosci = serwisy.cykliczne.harmonogram(DZIS)
    assert [(p.termin, p.stan, p.kolejna) for p in platnosci] == [
        (date(2026, 10, 10), StanPlatnosci.CZEKA, True),
        (date(2026, 11, 10), StanPlatnosci.CZEKA, False),
        (date(2026, 11, 30), StanPlatnosci.NADCHODZI, True),
    ]
    assert do_zaplaty(platnosci) == Decimal("200")
    serwisy.cykliczne.zaksieguj(platnosci[0].cykliczna, date(2026, 11, 10))
    stany = [p.stan for p in serwisy.cykliczne.harmonogram(DZIS)]
    assert stany == [StanPlatnosci.ZALATWIONA, StanPlatnosci.NADCHODZI]


def test_zaplata_przed_terminem(serwisy):
    cykliczna = serwisy.cykliczne.dodaj(czynsz(start=date(2026, 11, 30)), DZIS)
    transakcja = serwisy.cykliczne.zaksieguj(cykliczna, date(2026, 11, 30), DZIS)
    assert transakcja.data == DZIS
    assert serwisy.cykliczne.pobierz(cykliczna.id).nastepny == date(2026, 12, 30)
    assert serwisy.cykliczne.suma_do(date(2026, 11, 30)) == 0


def test_inna_kwota_w_kazdym_miesiacu(serwisy):
    pensja = czynsz(start=date(2026, 9, 10), rodzaj="przychód", kategoria_id=3, zmienna=True)
    serwisy.cykliczne.dodaj(pensja, DZIS)
    assert serwisy.cykliczne.srednia(pensja) is None
    for miesiac, kwota in ((9, "5000"), (10, "5200"), (11, "4800.01")):
        obecna = serwisy.cykliczne.pobierz(pensja.id)
        serwisy.cykliczne.zaksieguj(obecna, date(2026, miesiac, 10), DZIS, Decimal(kwota))
    obecna = serwisy.cykliczne.pobierz(pensja.id)
    kwoty = [t.kwota for t in serwisy.transakcje.wszystkie() if t.cykliczna_id == pensja.id]
    assert kwoty == [Decimal("5000"), Decimal("5200"), Decimal("4800.01")]
    assert obecna.zmienna is True
    assert serwisy.cykliczne.bilans().przychody == Decimal("4800.01")
    assert serwisy.cykliczne.srednia(obecna) == Decimal("5000.00")

    (platnosc,) = serwisy.cykliczne.harmonogram(DZIS)
    assert platnosc.do_poprawy is True
    serwisy.cykliczne.popraw(obecna, platnosc.transakcja, Decimal("4900"))
    (platnosc,) = serwisy.cykliczne.harmonogram(DZIS)
    assert platnosc.wplyw == Decimal("4900")
    assert serwisy.cykliczne.bilans().przychody == Decimal("4900.00")


def test_pominietego_terminu_nie_mozna_poprawic(serwisy):
    pensja = serwisy.cykliczne.dodaj(czynsz(start=date(2026, 10, 10), zmienna=True), DZIS)
    serwisy.cykliczne.zaksieguj(pensja, date(2026, 10, 10), DZIS, Decimal("70"))
    serwisy.cykliczne.pomin(serwisy.cykliczne.pobierz(pensja.id), date(2026, 11, 10))
    (platnosc,) = serwisy.cykliczne.harmonogram(DZIS)
    assert (platnosc.transakcja, platnosc.do_poprawy) == (None, False)
    assert platnosc.wplyw == Decimal("-70")


def test_zmiana(serwisy):
    stara = serwisy.cykliczne.dodaj(czynsz(), DZIS)
    inna = czynsz()
    inna.nazwa = "Internet"
    serwisy.cykliczne.dodaj(inna, DZIS)
    serwisy.cykliczne.zmien(replace(stara, nazwa="czynsz", kwota=Decimal("250")))
    assert serwisy.cykliczne.pobierz(stara.id).kwota == Decimal("250")
    with pytest.raises(BladWalidacji):
        serwisy.cykliczne.zmien(replace(stara, nazwa="internet"))


def test_przeplanowanie():
    stara = czynsz(start=date(2026, 8, 31), ostatnia=date(2026, 10, 31))
    assert stara.przeplanuj(date(2026, 11, 30), Czestotliwosc.MIESIAC) == stara
    nowa = stara.przeplanuj(date(2026, 11, 15), Czestotliwosc.KWARTAL)
    assert list(nowa.niezaksiegowane(date(2027, 3, 1))) == [
        date(2026, 11, 15),
        date(2027, 2, 15),
    ]
    with pytest.raises(NieprawidlowaData):
        stara.przeplanuj(date(2026, 10, 31), Czestotliwosc.MIESIAC)


def test_zapis_i_odczyt(serwisy):
    dodana = serwisy.cykliczne.dodaj(czynsz(ostatnia=date(2026, 10, 10)), DZIS)
    assert serwisy.cykliczne.wszystkie() == [dodana]
    with pytest.raises(BladWalidacji):
        serwisy.cykliczne.dodaj(czynsz(), DZIS)


def test_zbyt_stary_start(serwisy):
    with pytest.raises(NieprawidlowaData):
        serwisy.cykliczne.dodaj(czynsz(start=date(2025, 1, 1)), DZIS)


def test_zalegle_sa_posortowane(serwisy):
    serwisy.cykliczne.dodaj(czynsz(), DZIS)
    pensja = czynsz(start=date(2026, 10, 1), rodzaj="przychód", kategoria_id=3)
    pensja.nazwa = "Pensja"
    serwisy.cykliczne.dodaj(pensja, DZIS)
    assert [(c.nazwa, t.month) for c, t in serwisy.cykliczne.zalegle(DZIS)] == [
        ("Czynsz", 9),
        ("Pensja", 10),
        ("Czynsz", 10),
        ("Pensja", 11),
        ("Czynsz", 11),
    ]
    assert serwisy.cykliczne.suma_do(date(2026, 12, 31)) == Decimal("-100.00")


def test_ksiegowanie_i_pomijanie(serwisy):
    serwisy.cykliczne.dodaj(czynsz(), DZIS)
    (cykliczna, pierwszy), (_, drugi), _ = serwisy.cykliczne.zalegle(DZIS)
    transakcja = serwisy.cykliczne.zaksieguj(cykliczna, pierwszy)
    assert (transakcja.data, transakcja.opis, transakcja.cykliczna_id) == (pierwszy, "Czynsz", 1)
    serwisy.cykliczne.pomin(cykliczna, drugi)
    assert [t for _, t in serwisy.cykliczne.zalegle(DZIS)] == [date(2026, 11, 10)]


def test_wylaczona_nie_ma_zaleglosci(serwisy):
    cykliczna = serwisy.cykliczne.przelacz(serwisy.cykliczne.dodaj(czynsz(), DZIS))
    assert serwisy.cykliczne.zalegle(DZIS) == []
    assert serwisy.cykliczne.suma_do(DZIS) == 0
    assert serwisy.cykliczne.przelacz(cykliczna).aktywna is True


def test_usuniecie_wzoru_zostawia_transakcje(serwisy):
    cykliczna = serwisy.cykliczne.dodaj(czynsz(), DZIS)
    transakcja = serwisy.cykliczne.zaksieguj(cykliczna, date(2026, 9, 10))
    serwisy.cykliczne.usun(cykliczna)
    assert serwisy.transakcje.pobierz(transakcja.id).cykliczna_id is None


def test_konto_wzoru_jest_chronione(serwisy, konta):
    serwisy.cykliczne.dodaj(czynsz(konto_id=3), DZIS)
    with pytest.raises(RekordWUzyciu):
        serwisy.konta.usun(konta[2])


def test_stara_baza_dostaje_nowe_kolumny(tmp_path):
    plik = tmp_path / "stara.db"
    polaczenie = sqlite3.connect(plik)
    polaczenie.executescript(
        """
        CREATE TABLE transakcje (
            id INTEGER PRIMARY KEY AUTOINCREMENT, rodzaj TEXT NOT NULL, data TEXT NOT NULL,
            grosze INTEGER NOT NULL, opis TEXT NOT NULL, konto_id INTEGER NOT NULL,
            konto_docelowe_id INTEGER, kategoria_id INTEGER, import_id INTEGER
        );
        INSERT INTO transakcje (rodzaj, data, grosze, opis, konto_id)
        VALUES ('wydatek', '2026-11-01', 100, 'Stara', 1);
        """
    )
    polaczenie.close()
    for _ in range(2):
        baza = Baza(plik)
        wiersz = baza.zapytaj("SELECT * FROM transakcje")[0]
        assert (wiersz["opis"], wiersz["cykliczna_id"], wiersz["waluta"]) == ("Stara", None, "PLN")
        baza.zamknij()
