"""Testy osób i aktualizacji starej tabeli stałych pozycji."""

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from skarbonka.models.cykliczna import Cykliczna
from skarbonka.models.enums import Czestotliwosc
from skarbonka.services.bilans_stalych import do_zaplaty, podziel
from skarbonka.services.osoby import WSPOLNE
from skarbonka.storage.baza import Baza
from skarbonka.wyjatki import BladWalidacji

DZIS = date(2026, 11, 24)


def stala(nazwa, rodzaj, kwota, osoba_id=None) -> Cykliczna:
    return Cykliczna(
        nazwa,
        rodzaj,
        Decimal(kwota),
        1,
        3 if rodzaj == "przychód" else 2,
        date(2026, 11, 10),
        Czestotliwosc.MIESIAC,
        osoba_id=osoba_id,
    )


@pytest.fixture
def ola(serwisy):
    return serwisy.osoby.dodaj("Ola")


@pytest.mark.parametrize("nazwa", ["ola", "Wspólne", "wszyscy"])
def test_zajeta_nazwa(serwisy, ola, nazwa):
    with pytest.raises(BladWalidacji):
        serwisy.osoby.dodaj(nazwa)


def test_zmiana_nazwy(serwisy, ola):
    serwisy.osoby.zmien(ola, "OLA")
    assert serwisy.osoby.nazwy() == {ola.id: "OLA"}
    assert serwisy.osoby.wybor() == {WSPOLNE: None, "OLA": ola.id}


def test_kazda_osoba_ma_swoj_bilans(serwisy, ola):
    jan = serwisy.osoby.dodaj("Jan")
    for pozycja in (
        stala("Pensja", "przychód", "5000", ola.id),
        stala("Czynsz", "wydatek", "1500", ola.id),
        stala("Czynsz", "wydatek", "900", jan.id),
        stala("Internet", "wydatek", "60"),
    ):
        serwisy.cykliczne.dodaj(pozycja, DZIS)
    bilanse = {g.nazwa: g.bilans.na_czysto for g in serwisy.cykliczne.grupy()}
    assert bilanse == {"Ola": 3470, "Jan": -930, WSPOLNE: -60}
    assert serwisy.cykliczne.bilans().na_czysto == bilanse["Ola"] + bilanse["Jan"] == 2540


@pytest.mark.parametrize(
    ("kwota", "na_ile", "oczekiwane"),
    [
        ("100", 2, ["50", "50"]),
        ("100", 3, ["33.34", "33.33", "33.33"]),
        ("-0.05", 2, ["-0.03", "-0.02"]),
        ("7.77", 1, ["7.77"]),
    ],
)
def test_podzial_nie_gubi_groszy(kwota, na_ile, oczekiwane):
    czesci = podziel(Decimal(kwota), na_ile)
    assert czesci == [Decimal(czesc) for czesc in oczekiwane]
    assert sum(czesci) == Decimal(kwota)


def test_wspolne_u_kazdej_osoby(serwisy, ola):
    serwisy.osoby.dodaj("Jan")
    serwisy.cykliczne.dodaj(stala("Dotacja", "przychód", "200"), DZIS)
    serwisy.cykliczne.dodaj(stala("Internet", "wydatek", "59.99"), DZIS)
    wylaczona = serwisy.cykliczne.dodaj(stala("Gaz", "wydatek", "80"), DZIS)
    serwisy.cykliczne.przelacz(wylaczona)
    grupa_oli, grupa_jana, wspolne = serwisy.cykliczne.grupy()
    assert [u.wplyw for u in grupa_oli.wspolne] == [100, Decimal("-30.00"), -40]
    assert (grupa_oli.wlasne, grupa_oli.wspolne[0].ulamek) == ([], "1/2")
    assert grupa_oli.bilans.na_czysto == Decimal("70.00")
    assert grupa_jana.bilans.na_czysto == Decimal("70.01")
    assert wspolne.bilans.na_czysto == Decimal("140.01")


def test_czesc_wspolnej_platnosci(serwisy, ola):
    serwisy.osoby.dodaj("Jan")
    czynsz = serwisy.cykliczne.dodaj(stala("Czynsz", "wydatek", "1500"), DZIS)
    (platnosc,) = serwisy.cykliczne.grupy()[0].platnosci(serwisy.cykliczne.harmonogram(DZIS))
    assert (platnosc.wplyw, platnosc.wspolna) == (-750, True)
    assert do_zaplaty([platnosc]) == 750
    serwisy.cykliczne.zaksieguj(czynsz, platnosc.termin, DZIS)
    assert serwisy.transakcje.wszystkie()[-1].kwota == 1500
    (platnosc,) = serwisy.cykliczne.grupy()[1].platnosci(serwisy.cykliczne.harmonogram(DZIS))
    assert (platnosc.wplyw, do_zaplaty([platnosc])) == (-750, 0)


def test_nazwa_powtarza_sie_tylko_u_roznych_osob(serwisy, ola):
    serwisy.cykliczne.dodaj(stala("Czynsz", "wydatek", "1"), DZIS)
    serwisy.cykliczne.dodaj(stala("Czynsz", "wydatek", "1", ola.id), DZIS)
    with pytest.raises(BladWalidacji):
        serwisy.cykliczne.dodaj(stala("czynsz", "wydatek", "1", ola.id), DZIS)


def test_transakcja_ma_imie_w_opisie(serwisy, ola):
    czynsz = serwisy.cykliczne.dodaj(stala("Czynsz", "wydatek", "1", ola.id), DZIS)
    transakcja = serwisy.cykliczne.zaksieguj(czynsz, date(2026, 11, 10), DZIS)
    assert transakcja.opis == "Czynsz (Ola)"


def test_usuniecie_osoby(serwisy, ola):
    czynsz = serwisy.cykliczne.dodaj(stala("Czynsz", "wydatek", "1", ola.id), DZIS)
    transakcja = serwisy.cykliczne.zaksieguj(czynsz, date(2026, 11, 10), DZIS)
    serwisy.osoby.usun(ola)
    assert serwisy.cykliczne.wszystkie() == []
    assert serwisy.transakcje.pobierz(transakcja.id).cykliczna_id is None


def test_stara_tabela_pozwala_powtarzac_nazwy(tmp_path):
    plik = tmp_path / "stara.db"
    polaczenie = sqlite3.connect(plik)
    polaczenie.executescript(
        """
        CREATE TABLE konta (id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT NOT NULL UNIQUE,
            typ TEXT NOT NULL, grosze_poczatkowe INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE kategorie (id INTEGER PRIMARY KEY AUTOINCREMENT,
            nazwa TEXT NOT NULL UNIQUE, czy_wydatek INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE cykliczne (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT NOT NULL UNIQUE,
            rodzaj TEXT NOT NULL, grosze INTEGER NOT NULL,
            konto_id INTEGER NOT NULL REFERENCES konta(id),
            kategoria_id INTEGER NOT NULL REFERENCES kategorie(id), start TEXT NOT NULL,
            czestotliwosc TEXT NOT NULL, ostatnia TEXT, aktywna INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE transakcje (
            id INTEGER PRIMARY KEY AUTOINCREMENT, rodzaj TEXT NOT NULL, data TEXT NOT NULL,
            grosze INTEGER NOT NULL, opis TEXT NOT NULL, konto_id INTEGER NOT NULL,
            konto_docelowe_id INTEGER, kategoria_id INTEGER, import_id INTEGER,
            cykliczna_id INTEGER REFERENCES cykliczne(id) ON DELETE SET NULL
        );
        INSERT INTO konta (nazwa, typ) VALUES ('Portfel', 'gotówka');
        INSERT INTO kategorie (nazwa) VALUES ('Mieszkanie');
        INSERT INTO cykliczne VALUES
            (7, 'Czynsz', 'wydatek', 100, 1, 1, '2026-11-10', 'co miesiąc', NULL, 1);
        INSERT INTO transakcje (rodzaj, data, grosze, opis, konto_id, cykliczna_id)
            VALUES ('wydatek', '2026-11-10', 100, 'Czynsz', 1, 7);
        """
    )
    polaczenie.close()
    for _ in range(2):
        baza = Baza(plik)
        wiersz = dict(baza.zapytaj("SELECT * FROM cykliczne")[0])
        assert (wiersz["id"], wiersz["nazwa"], wiersz["osoba_id"]) == (7, "Czynsz", None)
        assert baza.zapytaj("SELECT cykliczna_id FROM transakcje")[0][0] == 7
        assert baza.zapytaj("PRAGMA foreign_key_check") == []
        assert baza.zapytaj("PRAGMA foreign_keys")[0][0] == 1
        baza.zamknij()
    baza = Baza(plik)
    baza.wstaw("cykliczne", wiersz | {"id": None})
    baza.wykonaj("DELETE FROM cykliczne WHERE id = 7")
    assert baza.zapytaj("SELECT cykliczna_id FROM transakcje")[0][0] is None
    assert baza.zapytaj("SELECT id FROM cykliczne")[0][0] == 8
    baza.zamknij()
