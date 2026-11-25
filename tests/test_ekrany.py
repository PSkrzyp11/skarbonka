"""Testy ekranów: cały przebieg od wyboru opcji do zapisanych danych."""

import webbrowser
from datetime import date
from decimal import Decimal

import pytest

from skarbonka import demo
from skarbonka.config import KATALOG_PROJEKTU
from skarbonka.services.zestaw import dodaj_dane_startowe, utworz_serwisy
from skarbonka.storage.baza import Baza
from skarbonka.ui.ekran_analizy import EkranAnaliz
from skarbonka.ui.ekran_cykliczne import EkranCyklicznych
from skarbonka.ui.ekran_dane import EkranDanych
from skarbonka.ui.ekran_osoby import EkranOsob
from skarbonka.ui.ekran_plan import EkranBudzetow, EkranCeli, EkranPlanu
from skarbonka.ui.ekran_profile import EkranProfili
from skarbonka.ui.ekran_reguly import EkranRegul
from skarbonka.ui.ekran_transakcje import EkranTransakcji
from skarbonka.ui.ekran_ustawienia import EkranKategorii, EkranKont, EkranUstawien
from skarbonka.ui.ekran_wykresy import EkranWykresow
from skarbonka.wyjatki import BladKursu

DZIEN = "01.11.2026"
WYCIAG = str(KATALOG_PROJEKTU / "przyklady" / "wyciag_demo.csv")


@pytest.fixture
def uruchom(odpowiedzi, capsys):
    """Zwraca funkcję, która przechodzi przez ekran i oddaje to, co wypisał."""

    def wykonaj(ekran, *teksty: str) -> str:
        odpowiedzi(*teksty, "0")
        ekran.uruchom()
        wyjscie = capsys.readouterr().out
        assert "Nieoczekiwany błąd" not in wyjscie
        return wyjscie

    return wykonaj


@pytest.fixture
def pelne(tmp_path):
    """Serwisy na bazie w pliku, wypełnionej danymi demonstracyjnymi."""
    baza = Baza(tmp_path / "pelna.db")
    serwisy = utworz_serwisy(baza)
    dodaj_dane_startowe(serwisy)
    demo.wypelnij(baza, serwisy)
    yield serwisy
    baza.zamknij()


def ostatnia(serwisy):
    return serwisy.transakcje.wszystkie()[-1]


def test_dodanie_przychodu(serwisy, uruchom):
    uruchom(EkranTransakcji(serwisy), "2", "2", "100", DZIEN, "Zwrot")
    assert (ostatnia(serwisy).wplyw, ostatnia(serwisy).konto_id) == (Decimal("100"), 2)


def test_ostrzezenie_po_wydatku(serwisy, uruchom):
    serwisy.budzety.ustaw(1, date(2026, 11, 1), Decimal("100"))
    wyjscie = uruchom(EkranTransakcji(serwisy), "1", "1", "20", DZIEN, "Obiad", "1")
    assert "Budżet Jedzenie: przekroczony" in wyjscie


def test_dodanie_przelewu(serwisy, uruchom):
    uruchom(EkranTransakcji(serwisy), "3", "1", "2", "50", DZIEN)
    assert ostatnia(serwisy).konto_docelowe_id == 3
    assert serwisy.konta.saldo(3) == Decimal("50")


def test_przelew_wymaga_dwoch_kont(baza, tmp_path, uruchom):
    serwisy = utworz_serwisy(baza, tmp_path)
    dodaj_dane_startowe(serwisy)
    assert "co najmniej dwóch kont" in uruchom(EkranTransakcji(serwisy), "3")


def test_wydatek_w_walucie(serwisy, uruchom):
    serwisy.waluty._pobierz = lambda waluta, dzien: Decimal("4.25")
    wyjscie = uruchom(EkranTransakcji(serwisy), "4", "1", "1", "10", DZIEN, "Obiad", "1")
    assert "4,2500 zł" in wyjscie
    assert (ostatnia(serwisy).kwota, ostatnia(serwisy).kwota_oryg) == (Decimal("42.50"), 10)


def test_kurs_wpisany_recznie(serwisy, uruchom):
    def brak_internetu(waluta, dzien):
        raise BladKursu("brak połączenia")

    serwisy.waluty._pobierz = brak_internetu
    uruchom(EkranTransakcji(serwisy), "4", "1", "1", "10", DZIEN, "abc", "5", "Obiad", "1")
    assert ostatnia(serwisy).kwota == Decimal("50")


def test_szukanie(serwisy, uruchom):
    wyjscie = uruchom(EkranTransakcji(serwisy), "6", "", "", "1", "", "kawa", "")
    assert "Pokazano 2 z 2" in wyjscie
    assert "120,00 zł" in wyjscie
    assert "Brak transakcji." in uruchom(EkranTransakcji(serwisy), "6", "", "", "", "", "xyz", "")


def test_edycja_wydatku(serwisy, uruchom):
    uruchom(EkranTransakcji(serwisy), "7", "3", "310", "", "Nowy czynsz", "", "1")
    zmieniona = serwisy.transakcje.pobierz(3)
    assert (zmieniona.kwota, zmieniona.opis) == (Decimal("310"), "Nowy czynsz")
    assert (zmieniona.konto_id, zmieniona.kategoria_id) == (1, 2)


def test_edycja_przelewu_i_anulowanie(serwisy, uruchom):
    uruchom(EkranTransakcji(serwisy), "7", "5", "999", "", "", "7", "5", "1", "anuluj")
    assert serwisy.transakcje.pobierz(5).kwota == Decimal("999")


def test_usuwanie(serwisy, uruchom):
    wyjscie = uruchom(EkranTransakcji(serwisy), "8", "1", "n", "8", "1", "t", "8", "99")
    assert "Nie ma pozycji o numerze 99." in wyjscie
    assert len(serwisy.transakcje.wszystkie()) == 4


def test_stronicowanie(pelne, uruchom):
    wyjscie = uruchom(EkranTransakcji(pelne), "5", "t", "n")
    assert "Pokazano 40 z" in wyjscie
    assert "Pokazano 60 z" not in wyjscie


def test_wszystkie_analizy(pelne, uruchom):
    wyjscie = uruchom(EkranAnaliz(pelne), "1", "2", "", "3", "", "4", "5", "6", "3", "01.2020")
    for fragment in ("Oszczędności", "Bilans", "Mieszkanie", "Pesymistycznie", "Brak wydatków"):
        assert fragment in wyjscie


def test_analizy_bez_danych(baza, tmp_path, uruchom):
    serwisy = utworz_serwisy(baza, tmp_path)
    ekran = EkranAnaliz(serwisy)
    wyjscie = uruchom(ekran, "1", "2", "", "3", "", "4", "5", "6", "7", "1", "", "2", "3", "0")
    assert "Prognoza wymaga" in wyjscie


def test_wykresy(pelne, uruchom, monkeypatch):
    otwarte = []
    monkeypatch.setattr(webbrowser, "open", otwarte.append)
    uruchom(EkranWykresow(pelne), "1", "", "t", "2", "n", "3", "n")
    pliki = {p.name.split("-")[0] for p in (pelne.katalog / "wykresy").iterdir()}
    assert pliki == {"kategorie", "trend", "saldo"}
    assert len(otwarte) == 1
    assert otwarte[0].startswith("file:///")


def test_budzety(serwisy, uruchom):
    ekran = EkranBudzetow(serwisy)
    wyjscie = uruchom(ekran, "1", "11.2026", "2", "11.2026", "1", "500", "1", "11.2026")
    assert "Brak budżetów" in wyjscie
    assert "20,0%" in wyjscie
    uruchom(ekran, "3", "12.2026", "4", "11.2026", "t", "4", "12.2026", "n")
    assert serwisy.budzety.z_miesiaca(date(2026, 11, 1)) == []
    assert len(serwisy.budzety.z_miesiaca(date(2026, 12, 1))) == 1


def test_cele(serwisy, uruchom):
    ekran = EkranCeli(serwisy)
    wyjscie = uruchom(ekran, "1", "2", "Wakacje", "1000", "01.01.2099", "3", "1000", "4", "n")
    assert "Brak celów." in wyjscie
    assert "osiągnięty" in wyjscie
    uruchom(ekran, "4", "t")
    assert serwisy.cele.wszystkie() == []


def test_cykliczne(serwisy, uruchom):
    ekran = EkranCyklicznych(serwisy)
    dzis = f"{date.today():%d.%m.%Y}"
    dodawanie = ("2", "Czynsz", "1", "100", "", "1", "2", "2", dzis)
    wyjscie = uruchom(ekran, "1", "3", *dodawanie, "1", "3", "3", "3", "1")
    assert "Brak stałych pozycji." in wyjscie
    assert ostatnia(serwisy).cykliczna_id == 1
    assert "wyłączona" in uruchom(ekran, "4", "5", "n", "5", "t")
    assert serwisy.cykliczne.wszystkie() == []


def test_bilans_i_edycja_stalych(pelne, uruchom):
    ekran = EkranCyklicznych(pelne)
    wyjscie = uruchom(ekran, "1", "7", "6", "1", "Wypłata", "7000", "", "", "", "")
    assert "Zostaje na czysto" in wyjscie
    assert "8 226,01 zł" in wyjscie
    assert "Płatności" in wyjscie and "Pensja (Kuba)" in wyjscie
    assert "Zostało do zapłaty: 59,99 zł" in wyjscie
    assert pelne.cykliczne.pobierz(1).nazwa == "Wypłata"
    assert pelne.cykliczne.bilans().przychody == 11300
    assert pelne.cykliczne.pobierz(1).osoba_id == 1


def test_inna_kwota_co_miesiac(serwisy, uruchom):
    ekran = EkranCyklicznych(serwisy)
    dzis = f"{date.today():%d.%m.%Y}"
    wyjscie = uruchom(ekran, "2", "Pensja", "2", "4000", "2", "1", "2", dzis, "3", "1", "4321", "1")
    assert ostatnia(serwisy).kwota == 4321
    assert "za każdym razem inna kwota" in wyjscie
    assert serwisy.cykliczne.bilans().przychody == 4321
    uruchom(ekran, "6", "", "", "1", "", "")
    assert serwisy.cykliczne.pobierz(1).zmienna is False


def test_osoby(serwisy, uruchom):
    osoby = EkranOsob(serwisy)
    assert "Brak osób." in uruchom(osoby, "1", "2", "Ola", "2", "ola", "Jan", "3", "2", "Janek")
    assert [o.nazwa for o in serwisy.osoby.wszystkie()] == ["Ola", "Janek"]
    dzis = f"{date.today():%d.%m.%Y}"
    czynsz = ("Czynsz", "1", "700", "", "1", "2", "2", dzis)
    stale = EkranCyklicznych(serwisy)
    wyjscie = uruchom(stale, "2", "2", *czynsz, "2", "3", *czynsz, "2", "2", "czynsz", "anuluj")
    assert "jest już zajęta" in wyjscie
    assert "Czynsz (Ola)" in uruchom(stale, "3", "1", "1", "8", "1", "0")
    assert {c.osoba_id for c in serwisy.cykliczne.wszystkie()} == {1, 2}
    wyjscie = uruchom(osoby, "1", "4", "1", "n", "4", "1", "t")
    assert "-1 400,00 zł" in wyjscie
    assert [c.osoba_id for c in serwisy.cykliczne.wszystkie()] == [2]


def test_brak_platnosci(serwisy, uruchom):
    assert "Brak płatności w tym miesiącu." in uruchom(EkranCyklicznych(serwisy), "7")


def test_pominiecie_terminu(pelne, uruchom):
    przed = len(pelne.transakcje.wszystkie())
    uruchom(EkranCyklicznych(pelne), "3", "2")
    assert pelne.cykliczne.zalegle() == []
    assert len(pelne.transakcje.wszystkie()) == przed


def test_import_cofniecie_i_eksport(pelne, uruchom, tmp_path):
    ekran = EkranDanych(pelne)
    przed = len(pelne.transakcje.wszystkie())
    wyjscie = uruchom(
        ekran,
        *("1", f'"{WYCIAG}"', "2", "t"),
        *("1", WYCIAG, "2", "n"),
        *("1", WYCIAG, "2", "t", "n"),
    )
    assert "Nowe: 8, duplikaty: 0" in wyjscie
    assert "Nie ma czego importować." in wyjscie
    assert len(pelne.transakcje.wszystkie()) == przed + 8
    wyjscie = uruchom(ekran, "2", "n", "2", "t", "2")
    assert "Nie ma importu do cofnięcia." in wyjscie
    assert len(pelne.transakcje.wszystkie()) == przed

    plik = tmp_path / "eksport.csv"
    uruchom(ekran, "3", str(plik), "3", str(plik), "n", "3", str(plik), "t")
    assert len(plik.read_text(encoding="utf-8-sig").splitlines()) == przed + 1


def test_eksport_bez_transakcji(baza, tmp_path, uruchom):
    assert "Brak transakcji" in uruchom(EkranDanych(utworz_serwisy(baza, tmp_path)), "3")


def test_raport_i_kopie(pelne, uruchom):
    ekran = EkranDanych(pelne)
    uruchom(ekran, "4", "", "")
    assert len(list((pelne.katalog / "raporty").iterdir())) == 1
    przed = pelne.transakcje.wszystkie()
    uruchom(ekran, "5")
    pelne.transakcje.usun(przed[0])
    wyjscie = uruchom(ekran, "6", "1", "n", "6", "1", "t", "6", "3", "brak.json")
    assert "Przywrócono dane" in wyjscie
    assert "Nie ma pliku" in wyjscie
    assert pelne.transakcje.wszystkie() == przed


def test_profile(serwisy, uruchom, tmp_path):
    plik = tmp_path / "bank.csv"
    plik.write_text("Wyciąg\nDzień,Opis,Suma\n1,2,3\n", encoding="utf-8")
    ekran = EkranProfili(serwisy)
    wyjscie = uruchom(ekran, "2", "Bank", str(plik), "2", "1", "1", "1", "3", "2", "1", "3", "n")
    assert "Bank: Dzień, Suma, Opis" in wyjscie
    uruchom(ekran, "3", "t")
    assert serwisy.profile.wlasne() == []


def test_reguly(serwisy, uruchom):
    ekran = EkranRegul(serwisy)
    wyjscie = uruchom(ekran, "1", "2", "kino", "4", "", "1", "4", "3", "n")
    assert "Brak reguł." in wyjscie
    assert "„kino” -> Rozrywka (priorytet 0)" in wyjscie
    uruchom(ekran, "3", "t")
    assert serwisy.kategoryzator.wszystkie() == []


def test_konta(serwisy, uruchom):
    wyjscie = uruchom(
        EkranKont(serwisy), "1", "2", "ror", "Bank", "2", "-10,50", "3", "1", "t", "3", "4", "t"
    )
    assert "jest już zajęta" in wyjscie
    assert "Nie można usunąć konta" in wyjscie
    assert "Bank" not in serwisy.konta.nazwy().values()


def test_kategorie(serwisy, uruchom):
    wyjscie = uruchom(
        EkranKategorii(serwisy), "1", "2", "Hobby", "t", "3", "1", "t", "3", "5", "t", "3", "4", "n"
    )
    assert "Wydatki: Jedzenie, Mieszkanie, Rozrywka" in wyjscie
    assert "Nie można usunąć kategorii" in wyjscie
    assert "Hobby" not in serwisy.kategorie.nazwy().values()


def test_ustawienia_i_plan_prowadza_do_podmenu(serwisy, uruchom):
    uruchom(EkranUstawien(serwisy), "1", "0", "2", "0", "3", "0", "4", "0", "5", "101", "70")
    assert serwisy.ustawienia.wczytaj().prog_ostrzezen == 70
    uruchom(EkranPlanu(serwisy), "1", "0", "2", "0", "3", "0")
