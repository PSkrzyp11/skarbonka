"""Testy kopii zapasowych i ratowania uszkodzonej bazy."""

import json
from datetime import date
from decimal import Decimal

import pytest

from skarbonka.models.cykliczna import Cykliczna
from skarbonka.models.enums import Czestotliwosc
from skarbonka.models.kurs import Kurs
from skarbonka.models.transakcja import Wydatek
from skarbonka.services import kopie as modul_kopii
from skarbonka.services.zestaw import dodaj_dane_startowe, utworz_serwisy
from skarbonka.storage.baza import TABELE, Baza
from skarbonka.storage.repozytoria_planu import RepozytoriumKursow
from skarbonka.ui.ratunek import otworz_baze
from skarbonka.wyjatki import BladPliku, UszkodzonyPlik


@pytest.fixture
def plik_bazy(tmp_path):
    return tmp_path / "moja.db"


@pytest.fixture
def serwisy_plikowe(plik_bazy):
    """Serwisy na bazie w pliku, z jedną transakcją."""
    baza = Baza(plik_bazy)
    serwisy = utworz_serwisy(baza)
    dodaj_dane_startowe(serwisy)
    serwisy.transakcje.dodaj(Wydatek(date(2026, 11, 1), Decimal("10"), "Kawa", 1, 1))
    yield serwisy
    baza.zamknij()


def opisy(serwisy) -> list[str]:
    return [t.opis for t in serwisy.transakcje.wszystkie()]


def test_kopia_przywraca_te_same_dane(serwisy_plikowe):
    serwisy = serwisy_plikowe
    przed = (serwisy.konta.wszystkie(), serwisy.kategorie.wszystkie(), serwisy.transakcje.wszystkie())
    kopia = serwisy.kopie.utworz()
    serwisy.transakcje.usun(serwisy.transakcje.pobierz(1))
    serwisy.kategorie.dodaj("Nowa")

    serwisy.kopie.przywroc(kopia)
    po = (serwisy.konta.wszystkie(), serwisy.kategorie.wszystkie(), serwisy.transakcje.wszystkie())
    assert po == przed


def test_kopia_obejmuje_wszystkie_tabele(serwisy_plikowe):
    s = serwisy_plikowe
    dzien = date(2026, 11, 1)
    s.budzety.ustaw(1, dzien, Decimal("100"))
    s.cele.wplac(s.cele.dodaj("Wakacje", Decimal("1000"), dzien), Decimal("10"))
    s.kategoryzator.dodaj("kawa", s.kategorie.pobierz(1))
    s.importer.zapisz("plik.csv", [])
    cykliczna = Cykliczna(
        "Czynsz", "wydatek", Decimal("5"), 1, 1, date.today(), Czestotliwosc.MIESIAC
    )
    s.cykliczne.zaksieguj(s.cykliczne.dodaj(cykliczna), date.today())
    RepozytoriumKursow(s.kopie._baza).dodaj(Kurs("EUR", dzien, Decimal("4.25")))

    kopia = s.kopie.utworz()
    tresc = json.loads(kopia.read_text(encoding="utf-8"))["tabele"]
    assert set(tresc) == set(TABELE)
    assert all(tresc.values())
    s.kopie.przywroc(kopia)
    ponowna = json.loads(s.kopie.utworz("druga").read_text(encoding="utf-8"))["tabele"]
    assert ponowna == tresc


def test_przed_przywroceniem_powstaje_kopia(serwisy_plikowe):
    kopia = serwisy_plikowe.kopie.utworz()
    serwisy_plikowe.kopie.przywroc(kopia)
    assert any("przed-przywroceniem" in k.name for k in serwisy_plikowe.kopie.lista())


def test_liczba_rekordow_w_kopii(serwisy_plikowe):
    kopia = serwisy_plikowe.kopie.utworz()
    assert serwisy_plikowe.kopie.policz(kopia)["transakcje"] == 1


@pytest.mark.parametrize(
    "tresc",
    [
        "[]",
        '{"wersja": 2, "tabele": {}}',
        '{"wersja": 1}',
        '{"wersja": 1, "tabele": {"obca": []}}',
        '{"wersja": 1, "tabele": {"konta": {}}}',
        '{"wersja": 1, "tabele": {"konta": [{"nazwa": "bez numeru"}]}}',
        '{"wersja": 1, "tabele": {"konta": [{"id": 1, "x = 1; DROP": 1}]}}',
        '{"wersja": 1, "tabele": {"konta": [{"id": 1, "nazwa": "A", "typ": "zły"}]}}',
        '{"wersja": 1, "tabele": {"konta": [{"id": 1, "nazwa": null, "typ": "gotówka"}]}}',
        '{"wersja": 1, "tabele": {"konta": [{"id": 1, "nazwa": ["lista"], "typ": "gotówka"}]}}',
        '{"wersja": 1, "tabele": {"konta": [{"id": 1e400, "nazwa": "A", "typ": "gotówka"}]}}',
        '{"wersja": 1, "tabele": {"konta": [{"id": 99999999999999999999, "nazwa": "A"}]}}',
        '{"wersja": 1, "tabele": {"importy": [{"id": 1, "plik": "a", "utworzono": "kiedyś"}]}}',
    ],
)
def test_bledna_kopia_nie_zmienia_danych(serwisy_plikowe, tmp_path, tresc):
    zla = tmp_path / "zla.json"
    zla.write_text(tresc, encoding="utf-8")
    with pytest.raises(UszkodzonyPlik):
        serwisy_plikowe.kopie.przywroc(zla)
    assert opisy(serwisy_plikowe) == ["Kawa"]
    assert len(serwisy_plikowe.kategorie.wszystkie()) == 9


def test_transakcja_bez_konta_w_kopii(serwisy_plikowe):
    kopia = serwisy_plikowe.kopie.utworz()
    dane = json.loads(kopia.read_text(encoding="utf-8"))
    dane["tabele"]["konta"] = []
    kopia.write_text(json.dumps(dane), encoding="utf-8")
    with pytest.raises(UszkodzonyPlik):
        serwisy_plikowe.kopie.przywroc(kopia)
    assert opisy(serwisy_plikowe) == ["Kawa"]


def test_brak_kopii(serwisy_plikowe, tmp_path):
    with pytest.raises(BladPliku):
        serwisy_plikowe.kopie.przywroc(tmp_path / "brak.json")


def test_kopia_dzienna_powstaje_raz(serwisy_plikowe):
    assert serwisy_plikowe.kopie.utworz_dzienna() is not None
    assert serwisy_plikowe.kopie.utworz_dzienna() is None


def test_stare_kopie_automatyczne_sa_usuwane(serwisy_plikowe, monkeypatch):
    monkeypatch.setattr(modul_kopii, "ILE_AUTOMATYCZNYCH", 2)
    reczna = serwisy_plikowe.kopie.utworz("reczna")
    for dzien in (1, 2, 3):
        serwisy_plikowe.kopie.utworz(f"auto-2020010{dzien}")
    dzienna = serwisy_plikowe.kopie.utworz_dzienna()
    nazwy = {k.name for k in serwisy_plikowe.kopie.lista()}
    assert nazwy == {reczna.name, dzienna.name, "moja-auto-20200103.json"}


def test_pusta_baza_nie_ma_kopii_dziennej(plik_bazy):
    baza = Baza(plik_bazy)
    assert utworz_serwisy(baza).kopie.utworz_dzienna() is None
    baza.zamknij()


def zepsuj(plik_bazy) -> None:
    plik_bazy.write_text("to nie jest baza " * 500, encoding="utf-8")


def test_ratunek_przywraca_kopie(plik_bazy, odpowiedzi):
    baza = Baza(plik_bazy)
    serwisy = utworz_serwisy(baza)
    dodaj_dane_startowe(serwisy)
    serwisy.transakcje.dodaj(Wydatek(date(2026, 11, 1), Decimal("10"), "Kawa", 1, 1))
    serwisy.kopie.utworz()
    (plik_bazy.parent / "kopie" / "moja-zepsuta.json").write_text("{", encoding="utf-8")
    baza.zamknij()
    zepsuj(plik_bazy)

    odpowiedzi("t")
    uratowana = otworz_baze(plik_bazy)
    assert opisy(utworz_serwisy(uratowana)) == ["Kawa"]
    uratowana.zamknij()
    assert len(list(plik_bazy.parent.glob("moja.uszkodzona-*.db"))) == 1


@pytest.mark.parametrize("odpowiedz", ["n", "anuluj"])
def test_ratunek_bez_przywracania(plik_bazy, odpowiedzi, odpowiedz):
    kopia = plik_bazy.parent / "kopie" / "moja-1.json"
    kopia.parent.mkdir()
    kopia.write_text("{", encoding="utf-8")
    zepsuj(plik_bazy)
    odpowiedzi(odpowiedz)
    baza = otworz_baze(plik_bazy)
    assert opisy(utworz_serwisy(baza)) == []
    baza.zamknij()


def test_ratunek_gdy_wszystkie_kopie_zepsute(plik_bazy, odpowiedzi, capsys):
    kopia = plik_bazy.parent / "kopie" / "moja-1.json"
    kopia.parent.mkdir()
    kopia.write_text("{", encoding="utf-8")
    zepsuj(plik_bazy)
    odpowiedzi("t")
    otworz_baze(plik_bazy).zamknij()
    assert "Żadnej kopii" in capsys.readouterr().out
