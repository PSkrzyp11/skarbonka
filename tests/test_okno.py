"""Testy okna. Są pomijane tam, gdzie nie ma ekranu."""

import gc
import tkinter as tk
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from tkinter import filedialog, messagebox
from typing import Any

import pytest

from skarbonka import demo
from skarbonka.config import KATALOG_PROJEKTU
from skarbonka.gui import formularze_transakcji as formularze
from skarbonka.gui import komunikaty, styl
from skarbonka.gui.okno import WIDOKI, Okno
from skarbonka.gui.okno_importu import OknoImportu
from skarbonka.models.importy import ProfilCSV
from skarbonka.models.transakcja import Przychod, Wydatek
from skarbonka.services.profile import PROFIL_SKARBONKI
from skarbonka.services.zestaw import dodaj_dane_startowe, utworz_serwisy
from skarbonka.storage.baza import Baza
from skarbonka.wyjatki import (
    BladKursu,
    BladPliku,
    BladWalidacji,
    NieZnalezionoRekordu,
    RekordWUzyciu,
)

WYCIAG = KATALOG_PROJEKTU / "przyklady" / "wyciag_demo.csv"
DZIEN = "01.11.2026"
PROBY = 5


def z_ponowieniem(akcja: Callable[[], Any]) -> Any:
    """Ponawia akcję, bo Tk bywa zawodny po otwarciu wielu okien w jednym procesie."""
    for proba in range(PROBY):
        try:
            return akcja()
        except tk.TclError as blad:
            if "display" in str(blad):
                pytest.skip(f"brak ekranu: {blad}")
            if proba == PROBY - 1:
                raise
            gc.collect()


@pytest.fixture
def otworz():
    """Zwraca funkcję otwierającą niewidoczne okno. Po teście je zamyka."""
    okna = []

    def wykonaj(serwisy) -> Okno:
        okno = z_ponowieniem(lambda: Okno(serwisy))
        okno.withdraw()
        okna.append(okno)
        return okno

    yield wykonaj
    for okno in okna:
        okno.update_idletasks()
        okno.destroy()


@pytest.fixture
def okno(otworz, serwisy) -> Okno:
    """Okno na małych danych testowych."""
    return otworz(serwisy)


@pytest.fixture
def pelne(otworz, tmp_path):
    """Okno na danych demonstracyjnych zapisanych w pliku."""
    baza = Baza(tmp_path / "pelna.db")
    serwisy = utworz_serwisy(baza)
    dodaj_dane_startowe(serwisy)
    demo.wypelnij(baza, serwisy)
    yield otworz(serwisy)
    baza.zamknij()


@pytest.fixture
def odpowiedz(monkeypatch):
    """Zwraca funkcję ustawiającą odpowiedzi okienek systemowych."""

    def ustaw(tak: bool = True, otworz: str = "", zapisz: str = "") -> None:
        monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: tak)
        monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(otworz))
        monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **k: str(zapisz))

    return ustaw


def wypelnij(formularz, **wartosci) -> None:
    """Wpisuje wartości i zatwierdza formularz."""
    for klucz, tekst in wartosci.items():
        formularz.ustaw(klucz, tekst)
    formularz.zatwierdz()


def ostatnia(okno):
    return okno.serwisy.transakcje.wszystkie()[-1]


@pytest.mark.parametrize("motyw", ["jasny", "ciemny"])
def test_wszystkie_widoki_sie_otwieraja(pelne, motyw):
    if motyw == "ciemny":
        pelne.zmien_motyw()
    for klasa in WIDOKI:
        pelne.pokaz_widok(klasa.TYTUL)
        pelne.update_idletasks()
        assert isinstance(pelne.widok(), klasa)
    pelne.pokaz_widok("Analizy")
    for rodzaj in ("Trend", "Saldo", "Kategorie"):
        pelne.widok().rodzaj.set(rodzaj)
        pelne.odswiez()
        assert pelne.widok().wykres.rysunek is not None
    assert styl.czy_ciemny() is (motyw == "ciemny")
    styl.ustaw_motyw("jasny")


def test_puste_dane(baza, tmp_path, otworz):
    okno = otworz(utworz_serwisy(baza, tmp_path))
    for klasa in WIDOKI:
        okno.pokaz_widok(klasa.TYTUL)
    with pytest.raises(NieZnalezionoRekordu):
        formularze.nowa_transakcja(okno, Wydatek)
    okno.pokaz_widok("Analizy")
    with pytest.raises(BladPliku):
        okno.widok().zapisz_png()


def test_motyw_jest_zapamietany(okno):
    okno.zmien_motyw()
    assert okno.serwisy.ustawienia.wczytaj().motyw == "ciemny"
    okno.zmien_motyw()
    assert okno.serwisy.ustawienia.wczytaj().motyw == "jasny"


def test_pulpit_pokazuje_liczby(pelne):
    kafelek = pelne.widok().kafelki[0]
    assert kafelek._wartosc.cget("text").endswith("zł")
    assert pelne.widok().tabela.liczba() == 6


def test_dodanie_wydatku_i_ostrzezenie(okno):
    okno.serwisy.budzety.ustaw(1, date(2026, 11, 1), Decimal("100"))
    formularz = formularze.nowa_transakcja(okno, Wydatek)
    wypelnij(formularz, kwota="20,50", data=DZIEN, opis="Obiad")
    assert (ostatnia(okno).kwota, ostatnia(okno).opis) == (Decimal("20.50"), "Obiad")
    assert "Budżet Jedzenie: przekroczony" in okno.tekst_powiadomienia()
    assert not formularz.winfo_exists()


def test_bledne_pola_zostawiaja_formularz(okno, transakcje):
    formularz = formularze.nowa_transakcja(okno, Przychod)
    wypelnij(formularz, kwota="abc", data="31.02.2026", opis="")
    assert formularz.winfo_exists()
    assert "nie jest kwotą" in formularz._bledy["kwota"].cget("text")
    assert "nie jest poprawną datą" in formularz._bledy["data"].cget("text")
    assert len(okno.serwisy.transakcje.wszystkie()) == len(transakcje)
    wypelnij(formularz, kwota="100", data=DZIEN, opis="Zwrot")
    assert ostatnia(okno).wplyw == Decimal("100")


def test_regula_podpowiada_kategorie(okno, kategorie):
    okno.serwisy.kategoryzator.dodaj("kino", kategorie[3])
    formularz = formularze.nowa_transakcja(okno, Wydatek)
    formularz.ustaw("opis", "Kino Centrum")
    formularz._zmieniono(formularz._pola["opis"])
    assert formularz.wartosc("kategoria") == "Rozrywka"
    formularz.destroy()


def test_przelew(okno):
    wypelnij(formularze.nowy_przelew(okno), kwota="50", data=DZIEN, zrodlo="Portfel", cel="Lokata")
    assert okno.serwisy.konta.saldo(3) == Decimal("50")
    formularz = formularze.nowy_przelew(okno)
    wypelnij(formularz, kwota="50", data=DZIEN, zrodlo="ROR", cel="ROR")
    assert "dwóch różnych kont" in formularz._blad_ogolny.cget("text")
    formularz.destroy()


def test_przelew_wymaga_dwoch_kont(baza, tmp_path, otworz):
    serwisy = utworz_serwisy(baza, tmp_path)
    dodaj_dane_startowe(serwisy)
    with pytest.raises(BladWalidacji):
        formularze.nowy_przelew(otworz(serwisy))


def test_wydatek_w_walucie(okno):
    def brak_internetu(waluta, dzien):
        raise BladKursu("brak połączenia")

    okno.serwisy.waluty._pobierz = brak_internetu
    formularz = formularze.wydatek_w_walucie(okno)
    wypelnij(formularz, kwota="10", data=DZIEN, opis="Muzeum")
    assert "brak połączenia" in formularz._blad_ogolny.cget("text")
    wypelnij(formularz, kurs="4,25")
    assert (ostatnia(okno).kwota, ostatnia(okno).waluta) == (Decimal("42.50"), "EUR")
    okno.serwisy.waluty._pobierz = lambda waluta, dzien: Decimal("5")
    wypelnij(formularze.wydatek_w_walucie(okno), kwota="10", data=DZIEN, opis="Obiad")
    assert ostatnia(okno).kwota == Decimal("50")


def test_filtry_transakcji(okno):
    okno.pokaz_widok("Transakcje")
    widok = okno.widok()
    assert widok.tabela.liczba() == 5
    widok.fraza.insert(0, "kawa")
    widok.odswiez()
    assert widok.tabela.liczba() == 2
    assert "120,00 zł" in widok.podsumowanie.cget("text")
    widok.od.insert(0, "01.11.2026")
    widok.odswiez()
    assert widok.tabela.liczba() == 1
    widok.wyczysc_filtry()
    widok.konto.set("ROR")
    widok.kategoria.set("Mieszkanie")
    widok.odswiez()
    assert widok.tabela.liczba() == 1
    widok.od.insert(0, "abc")
    with pytest.raises(BladWalidacji):
        widok.odswiez()


def test_sortowanie_po_kwocie(okno):
    okno.pokaz_widok("Transakcje")
    tabela = okno.widok().tabela
    tabela._sortuj(4)
    rosnaco = tabela.drzewo.get_children()
    tabela._sortuj(4)
    assert tabela.drzewo.get_children() == rosnaco[::-1]
    assert rosnaco[-1] == "2"


def test_edycja_i_usuwanie(okno, odpowiedz):
    okno.pokaz_widok("Transakcje")
    widok = okno.widok()
    with pytest.raises(NieZnalezionoRekordu):
        widok.edytuj()
    formularz = formularze.edycja(okno, okno.serwisy.transakcje.pobierz(3))
    wypelnij(formularz, kwota="310", konto="Portfel")
    zmieniona = okno.serwisy.transakcje.pobierz(3)
    assert (zmieniona.kwota, zmieniona.konto_id) == (Decimal("310"), 1)
    wypelnij(formularze.edycja(okno, okno.serwisy.transakcje.pobierz(5)), opis="Zasilenie")
    assert okno.serwisy.transakcje.pobierz(5).opis == "Zasilenie"
    for tak, zostaje in ((False, 5), (True, 4)):
        odpowiedz(tak=tak)
        widok.tabela.zaznacz(1)
        widok.usun()
        assert len(okno.serwisy.transakcje.wszystkie()) == zostaje


def test_budzety(okno, odpowiedz):
    odpowiedz(tak=True)
    okno.pokaz_widok("Plan")
    zakladka = okno.widok().zakladki["Budżety"]
    wypelnij(zakladka.ustaw(), kategoria="Jedzenie", limit="500")
    miesiac = zakladka.miesiac.miesiac
    assert len(okno.serwisy.budzety.z_miesiaca(miesiac)) == 1
    zakladka.miesiac.przesun(1)
    zakladka.skopiuj()
    assert "Skopiowane budżety: 1" in okno.tekst_powiadomienia()
    zakladka.usun(okno.serwisy.budzety.wykonanie(miesiac)[0])
    assert okno.serwisy.budzety.z_miesiaca(miesiac) == []


def test_cele(okno, odpowiedz):
    odpowiedz(tak=True)
    okno.pokaz_widok("Plan")
    zakladka = okno.widok().zakladki["Cele"]
    wypelnij(zakladka.dodaj(), nazwa="Rower", kwota="1000", termin="01.01.2099")
    powtorzony = zakladka.dodaj()
    wypelnij(powtorzony, nazwa="rower", kwota="1", termin="01.01.2099")
    assert "jest już zajęta" in powtorzony._bledy["nazwa"].cget("text")
    powtorzony.destroy()
    cel = okno.serwisy.cele.wszystkie()[0]
    wypelnij(zakladka.wplac(cel), kwota="1000")
    assert okno.serwisy.cele.wszystkie()[0].brakuje == 0
    zakladka.usun(cel)
    assert okno.serwisy.cele.wszystkie() == []


def test_cykliczne(okno, odpowiedz):
    odpowiedz(tak=True)
    okno.pokaz_widok("Plan")
    zakladka = okno.widok().zakladki["Cykliczne"]
    with pytest.raises(NieZnalezionoRekordu):
        zakladka.przelacz()
    formularz = zakladka.dodaj()
    wypelnij(formularz, nazwa="Czynsz", kwota="100", kategoria="Wynagrodzenie")
    assert "nie pasuje do rodzaju" in formularz._blad_ogolny.cget("text")
    wypelnij(formularz, kategoria="Mieszkanie")
    cykliczna, termin = okno.serwisy.cykliczne.zalegle()[0]
    zakladka.zaksieguj(cykliczna, termin)
    assert ostatnia(okno).cykliczna_id == cykliczna.id
    zakladka.tabela.zaznacz(cykliczna.id)
    zakladka.przelacz()
    assert okno.serwisy.cykliczne.wszystkie()[0].aktywna is False
    zakladka.tabela.zaznacz(cykliczna.id)
    zakladka.usun()
    assert okno.serwisy.cykliczne.wszystkie() == []


def test_pominiecie_terminu(pelne):
    pelne.pokaz_widok("Plan")
    cykliczna, termin = pelne.serwisy.cykliczne.zalegle()[0]
    pelne.widok().zakladki["Cykliczne"].pomin(cykliczna, termin)
    assert pelne.serwisy.cykliczne.zalegle() == []


def test_zapis_wykresu(pelne, odpowiedz, tmp_path):
    odpowiedz(zapisz=tmp_path / "wykres.png")
    pelne.pokaz_widok("Analizy")
    pelne.widok().zapisz_png()
    assert (tmp_path / "wykres.png").read_bytes().startswith(b"\x89PNG")


def test_import_i_cofniecie(okno, odpowiedz, transakcje):
    okno.pokaz_widok("Dane")
    widok = okno.widok()
    odpowiedz(otworz="")
    assert widok.importuj() is None
    odpowiedz(otworz=WYCIAG)
    wypelnij(widok.importuj(), profil="Skarbonka", konto="ROR")

    podglad = okno.serwisy.importer.przygotuj(WYCIAG, PROFIL_SKARBONKI, 2)
    OknoImportu(okno, podglad).zapisz()
    assert len(okno.serwisy.transakcje.wszystkie()) == len(transakcje) + 8

    drugi = OknoImportu(okno, okno.serwisy.importer.przygotuj(WYCIAG, PROFIL_SKARBONKI, 2))
    assert drugi.tabela.liczba() == 0
    drugi.z_duplikatami.select()
    drugi._pokaz()
    assert drugi.tabela.liczba() == 8
    drugi.destroy()

    odpowiedz(tak=True)
    widok.cofnij()
    assert okno.serwisy.transakcje.wszystkie() == transakcje
    with pytest.raises(NieZnalezionoRekordu):
        widok.cofnij()


def test_bledny_plik_importu(okno, odpowiedz, tmp_path):
    zly = tmp_path / "zly.csv"
    zly.write_text("a;b\n1;2\n", encoding="utf-8")
    odpowiedz(otworz=zly)
    okno.pokaz_widok("Dane")
    formularz = okno.widok().importuj()
    formularz.zatwierdz()
    assert "Brak kolumn" in formularz._blad_ogolny.cget("text")
    formularz.destroy()


def test_eksport_i_raport(okno, odpowiedz, tmp_path):
    okno.pokaz_widok("Dane")
    odpowiedz(zapisz=tmp_path / "eksport.csv")
    okno.widok().eksportuj()
    assert len((tmp_path / "eksport.csv").read_text(encoding="utf-8-sig").splitlines()) == 6
    odpowiedz(zapisz=tmp_path / "raport.txt")
    wypelnij(okno.widok().raport(), miesiac="11.2026")
    assert "listopad 2026" in (tmp_path / "raport.txt").read_text(encoding="utf-8")


def test_kopie(pelne, odpowiedz):
    pelne.pokaz_widok("Dane")
    widok = pelne.widok()
    with pytest.raises(NieZnalezionoRekordu):
        widok.przywroc_zaznaczona()
    przed = pelne.serwisy.transakcje.wszystkie()
    widok.utworz_kopie()
    pelne.serwisy.transakcje.usun(przed[0])
    odpowiedz(tak=False)
    widok.tabela.zaznacz(0)
    widok.przywroc_zaznaczona()
    assert len(pelne.serwisy.transakcje.wszystkie()) == len(przed) - 1
    odpowiedz(tak=True, otworz=pelne.serwisy.kopie.lista()[0])
    widok.przywroc_z_pliku()
    assert pelne.serwisy.transakcje.wszystkie() == przed


def test_ustawienia(okno, odpowiedz):
    odpowiedz(tak=True)
    okno.pokaz_widok("Ustawienia")
    zakladki = okno.widok().zakladki
    wypelnij(zakladki["Konta"].dodaj(), nazwa="Bank", saldo="-10,50")
    assert okno.serwisy.konta.saldo(4) == Decimal("-10.50")
    wypelnij(zakladki["Kategorie"].dodaj(), nazwa="Hobby")
    wypelnij(zakladki["Reguły"].dodaj(), fraza="gitara", kategoria="Hobby")
    assert okno.serwisy.kategoryzator.dopasuj("Gitara", Wydatek).nazwa == "Hobby"

    zakladki["Konta"].tabela.zaznacz(1)
    with pytest.raises(RekordWUzyciu):
        zakladki["Konta"].usun()
    for nazwa, numer in (("Konta", 4), ("Reguły", 1), ("Kategorie", 5)):
        zakladki[nazwa].tabela.zaznacz(numer)
        zakladki[nazwa].usun()
    assert "Bank" not in okno.serwisy.konta.nazwy().values()
    assert "Hobby" not in okno.serwisy.kategorie.nazwy().values()
    with pytest.raises(NieZnalezionoRekordu):
        zakladki["Konta"].usun()

    formularz = okno.widok().zmien_prog()
    wypelnij(formularz, prog="0")
    assert formularz.winfo_exists()
    wypelnij(formularz, prog="60")
    assert okno.serwisy.ustawienia.wczytaj().prog_ostrzezen == 60


def test_profile_csv(okno, odpowiedz, tmp_path):
    plik = tmp_path / "bank.csv"
    plik.write_text("Wyciąg\nDzień,Opis,Suma\n1,2,3\n", encoding="utf-8")
    odpowiedz(tak=True, otworz=plik)
    okno.pokaz_widok("Ustawienia")
    zakladka = okno.widok().zakladki["Profile CSV"]
    wypelnij(zakladka.dodaj(), nazwa="Bank", separator="przecinek (,)", pomin="1")
    profil = ProfilCSV("Bank", ",", "utf-8-sig", 1)
    wypelnij(zakladka.wybierz_kolumny(profil, ["Dzień", "Opis", "Suma"]), kwota="Suma", opis="Opis")
    assert okno.serwisy.profile.wlasne()[0].wymagane_kolumny == ("Dzień", "Suma", "Opis")
    zakladka.tabela.zaznacz(0)
    with pytest.raises(BladWalidacji):
        zakladka.usun()
    zakladka.tabela.zaznacz(1)
    zakladka.usun()
    assert okno.serwisy.profile.wlasne() == []


def test_blad_w_oknie_nie_zamyka_programu(okno, caplog):
    przewidziany = NieZnalezionoRekordu("Nie ma takiej pozycji.")
    okno.report_callback_exception(type(przewidziany), przewidziany, None)
    assert okno.tekst_powiadomienia() == "Nie ma takiej pozycji."
    okno.report_callback_exception(ZeroDivisionError, ZeroDivisionError("awaria"), None)
    assert "Nieoczekiwany błąd" in okno.tekst_powiadomienia()
    assert "awaria" in caplog.text


def test_komunikaty_bez_okna(monkeypatch):
    pokazane = []
    monkeypatch.setattr(messagebox, "showinfo", lambda tytul, tekst, **k: pokazane.append(tekst))
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    z_ponowieniem(lambda: komunikaty.pokaz("Uwaga"))
    assert pokazane == ["Uwaga"]
    assert z_ponowieniem(lambda: komunikaty.zapytaj("Na pewno?")) is True
