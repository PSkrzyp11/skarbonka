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
from skarbonka.gui import ikony, komunikaty, styl
from skarbonka.gui.lista import Naglowek, Pozycja
from skarbonka.gui.okno import WIDOKI, Okno
from skarbonka.gui.okno_importu import PanelImportu
from skarbonka.gui.pozycje import kwota_ze_znakiem
from skarbonka.gui.skladniki import Przewijana, etykieta
from skarbonka.gui.widok_transakcje import okresy
from skarbonka.models.cykliczna import Cykliczna
from skarbonka.models.enums import Czestotliwosc
from skarbonka.models.importy import ProfilCSV
from skarbonka.models.transakcja import Przychod, Wydatek
from skarbonka.services.profile import PROFIL_SKARBONKI
from skarbonka.services.zestaw import dodaj_dane_startowe, utworz_serwisy
from skarbonka.storage.baza import Baza
from skarbonka.utils.formatowanie import formatuj_kwote
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
        monkeypatch.setattr(Okno, "zapytaj", lambda self, *a, **k: tak)
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
    widok = pelne.widok()
    assert widok.saldo.cget("text") == kwota_ze_znakiem(formatuj_kwote(pelne.serwisy.konta.saldo()))
    assert widok.tabela.liczba() == 5
    assert widok.wykres.rysunek is not None


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
    assert "nie jest kwotą" in formularz.blad_pola("kwota")
    assert "nie jest poprawną datą" in formularz.blad_pola("data")
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
    assert "dwóch różnych kont" in formularz.blad_ogolny()
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
    assert "brak połączenia" in formularz.blad_ogolny()
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
    assert "120,00 zł" in widok.podtytul.cget("text")
    widok.wyczysc_filtry()
    widok.konto.set("ROR")
    widok.kategoria.set("Mieszkanie")
    widok.odswiez()
    assert widok.tabela.liczba() == 1
    widok.wyczysc_filtry()
    assert widok.tabela.liczba() == 5


def test_okresy():
    zakresy = okresy(date(2026, 1, 15))
    assert zakresy["Ten miesiąc"] == (date(2026, 1, 1), None)
    assert zakresy["Poprzedni miesiąc"] == (date(2025, 12, 1), date(2025, 12, 31))
    assert zakresy["Ostatnie 3 miesiące"] == (date(2025, 10, 15), None)
    assert zakresy["Ten rok"] == (date(2026, 1, 1), None)


def test_kolejnosc_i_grupowanie(okno):
    okno.pokaz_widok("Transakcje")
    widok = okno.widok()
    elementy = [element for _, _, element in widok.tabela._uklad]
    naglowki = [e for e in elementy if isinstance(e, Naglowek)]
    assert len(naglowki) == 5
    assert naglowki[0].tekst.startswith("Czwartek, 12 listopada")
    widok.kolejnosc.set("od największych kwot")
    widok.odswiez()
    assert [p.id for p in widok.tabela.pozycje()] == [2, 5, 3, 4, 1]
    assert len(widok.tabela._uklad) == 5


def test_zaznaczenie_pokazuje_przyciski(okno):
    okno.pokaz_widok("Transakcje")
    widok = okno.widok()
    widok.tabela.zaznacz(3)
    assert widok._nazwa_wybranej.cget("text") == "Czynsz"
    assert widok._akcje.winfo_manager() == "pack"
    widok.fraza.insert(0, "kawa")
    widok.odswiez()
    assert widok.tabela.zaznaczony() is None
    assert widok._akcje.winfo_manager() == ""


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
    assert okno.tekst_powiadomienia() == "Skopiowane budżety: 1"
    zakladka.usun(okno.serwisy.budzety.wykonanie(miesiac)[0])
    assert okno.serwisy.budzety.z_miesiaca(miesiac) == []


def test_cele(okno, odpowiedz):
    odpowiedz(tak=True)
    okno.pokaz_widok("Plan")
    zakladka = okno.widok().zakladki["Cele"]
    wypelnij(zakladka.dodaj(), nazwa="Rower", kwota="1000", termin="01.01.2099")
    powtorzony = zakladka.dodaj()
    wypelnij(powtorzony, nazwa="rower", kwota="1", termin="01.01.2099")
    assert "jest już zajęta" in powtorzony.blad_pola("nazwa")
    powtorzony.destroy()
    cel = okno.serwisy.cele.wszystkie()[0]
    wypelnij(zakladka.wplac(cel), kwota="1000")
    assert okno.serwisy.cele.wszystkie()[0].brakuje == 0
    zakladka.usun(cel)
    assert okno.serwisy.cele.wszystkie() == []


def test_stale_platnosci(okno, odpowiedz):
    okno.pokaz_widok("Stałe płatności")
    widok, serwis = okno.widok(), okno.serwisy.cykliczne
    assert widok._pusty.winfo_manager()
    with pytest.raises(NieZnalezionoRekordu):
        widok.przelacz()
    wypelnij(widok.dodaj_oplate(), nazwa="Czynsz", kwota="1500", kategoria="Mieszkanie")
    assert "Dodaj stały przychód" in widok._opis.cget("text")
    wypelnij(widok.dodaj_przychod(), nazwa="Pensja", kwota="1000")
    assert "wyższe" in widok._opis.cget("text")
    czynsz = serwis.wszystkie()[0]
    widok.tabela.zaznacz(czynsz.id)
    wypelnij(widok.edytuj(), kwota="250", odstep="1 rok")
    assert widok.na_czysto.cget("text") == "979,17 zł"
    assert okno.pasek._pozycje["Stałe płatności"]._licznik.cget("text") == "2"
    widok.zalatw(next(p for p in serwis.harmonogram() if p.cykliczna.id == czynsz.id))
    assert ostatnia(okno).cykliczna_id == czynsz.id
    widok.tabela.zaznacz(czynsz.id)
    widok.przelacz()
    assert serwis.pobierz(czynsz.id).aktywna is False
    for tak, zostaje in ((False, 2), (True, 1)):
        odpowiedz(tak=tak)
        widok.usun()
        assert len(serwis.wszystkie()) == zostaje


def test_osoby(okno, odpowiedz):
    okno.pokaz_widok("Stałe płatności")
    widok, serwisy = okno.widok(), okno.serwisy
    assert not widok.osoby.winfo_manager()
    for imie in ("Ola", "Jan"):
        wypelnij(widok.dodaj_osobe(), nazwa=imie)
        assert widok.osoby.nazwa_wybranej() == imie
        wypelnij(widok.dodaj_oplate(), nazwa="Czynsz", kwota="700", kategoria="Mieszkanie")
    wypelnij(widok.dodaj_przychod(), nazwa="Pensja", kwota="5000")
    assert widok.osoby.winfo_manager()
    assert widok.na_czysto.cget("text") == "4 300,00 zł"
    assert widok._czyje.cget("text").endswith("Jan")
    assert [p.tytul for p in widok.tabela.pozycje()] == ["Pensja", "Czynsz"]

    widok.osoby.lista.zaznacz(1)
    assert kwota_ze_znakiem("-700,00 zł") == widok.na_czysto.cget("text")
    wypelnij(widok.osoby.edytuj(), nazwa="Aleksandra")
    assert serwisy.osoby.pobierz(1).nazwa == "Aleksandra"
    widok.osoby.lista.zaznacz(0)
    assert widok.na_czysto.cget("text") == "3 600,00 zł"
    assert any("Aleksandra" in p.opis for p in widok.tabela.pozycje())
    widok.tabela.zaznacz(1)
    wypelnij(widok.edytuj(), osoba="Wspólne")
    assert serwisy.cykliczne.pobierz(1).osoba_id is None
    widok.osoby.lista.zaznacz(-1)
    assert [p.id for p in widok.tabela.pozycje()] == [1]
    assert widok.osoby.lista.pozycja(-1).podpis == kwota_ze_znakiem("po -350,00 zł")
    widok.osoby.lista.zaznacz(1)
    (czesc,) = widok.tabela.pozycje()
    assert (czesc.wartosc, czesc.podpis) == (kwota_ze_znakiem("-350,00 zł"), "z 700,00 zł")
    assert widok._do_zaplaty.cget("text") == "do zapłaty 350,00 zł"

    widok.osoby.lista.zaznacz(2)
    for tak, zostaje in ((False, 3), (True, 1)):
        odpowiedz(tak=tak)
        widok.osoby.usun()
        assert len(serwisy.cykliczne.wszystkie()) == zostaje
    assert widok.osoby.nazwa_wybranej() == "Wszyscy"


def test_inna_kwota_co_miesiac(okno):
    okno.pokaz_widok("Stałe płatności")
    widok, serwis = okno.widok(), okno.serwisy.cykliczne
    wypelnij(
        widok.dodaj_przychod(), nazwa="Pensja", kwota="4000", zmienna="Za każdym razem inna"
    )
    assert widok.tabela.pozycja(1).podpis == "kwota zmienna"
    pensja = serwis.harmonogram()[0]
    widok.zalatw(pensja)
    formularz = okno.panel
    assert formularz.wartosc("kwota") == "4000,00"
    wypelnij(formularz, kwota="abc")
    assert formularz.blad_pola("kwota")
    wypelnij(formularz, kwota="4321")
    assert ostatnia(okno).kwota == Decimal("4321")
    assert widok.na_czysto.cget("text") == "4 321,00 zł"
    wypelnij(widok.wpisz_kwote(serwis.harmonogram()[0]), kwota="4500,50")
    assert ostatnia(okno).kwota == Decimal("4500.50")
    assert widok.na_czysto.cget("text") == "4 500,50 zł"
    widok.tabela.zaznacz(1)
    wypelnij(widok.edytuj(), zmienna="Zawsze taka sama")
    assert serwis.pobierz(1).zmienna is False


def test_powtarzanie_co_2_miesiace(okno):
    okno.pokaz_widok("Stałe płatności")
    widok = okno.widok()
    formularz = widok.dodaj_oplate()
    odstep = formularz._kontrolki["odstep"]
    assert odstep.get() == "1 miesiąc"
    formularz.ustaw("odstep", "5 miesięcy")
    odstep.wpis.delete(0, "end")
    odstep.wpis.insert(0, "2")
    odstep._odmien()
    assert odstep.get() == "2 miesiące"
    assert odstep.menu.cget("values") == ["dni", "tygodnie", "miesiące", "kwartały", "lata"]
    for zly in ("0 miesiące", "x miesiące", " miesiące", "100 miesięcy"):
        wypelnij(formularz, nazwa="Prąd", kwota="300", odstep=zly)
        assert "od 1 do 99" in formularz.blad_pola("odstep")
    wypelnij(formularz, odstep="2 miesiące")
    assert widok.tabela.pozycja(1).opis.startswith("co 2 miesiące")
    assert widok.tabela.pozycja(1).podpis == kwota_ze_znakiem("-150,00 zł na miesiąc")
    widok.tabela.zaznacz(1)
    edycja = widok.edytuj()
    assert edycja.wartosc("odstep") == "2 miesiące"
    wypelnij(edycja, odstep="3 tygodnie")
    assert okno.serwisy.cykliczne.pobierz(1).powtarzanie == "co 3 tygodnie"


def test_srednia_zmiennej_pozycji(pelne):
    pelne.pokaz_widok("Stałe płatności")
    widok = pelne.widok()
    widok.tabela.zaznacz(1)
    wypelnij(widok.edytuj(), zmienna="Za każdym razem inna")
    assert widok.tabela.pozycja(1).podpis == "średnio 6 200,00 zł"


def test_powtorzona_nazwa_stalej(pelne):
    pelne.pokaz_widok("Stałe płatności")
    widok = pelne.widok()
    widok.tabela.zaznacz(1)
    formularz = widok.edytuj()
    wypelnij(formularz, nazwa="ubezpieczenie auta")
    assert "jest już zajęta" in formularz.blad_ogolny()
    wypelnij(formularz, nazwa="Pensja", termin="01.01.2020")
    assert formularz.blad_pola("termin")


def test_pominiecie_terminu(pelne):
    pelne.pokaz_widok("Stałe płatności")
    cykliczna, termin = pelne.serwisy.cykliczne.zalegle()[0]
    pelne.widok().pomin(cykliczna, termin)
    assert pelne.serwisy.cykliczne.zalegle() == []


def test_dluga_lista_platnosci(okno):
    for numer in range(25):
        okno.serwisy.cykliczne.dodaj(
            Cykliczna(
                f"Opłata {numer}",
                "wydatek",
                Decimal("1"),
                1,
                1,
                date.today(),
                Czestotliwosc.MIESIAC,
            )
        )
    okno.pokaz_widok("Stałe płatności")
    ostatni = okno.widok()._platnosci.winfo_children()[-1]
    assert ostatni.cget("text") == "Kolejne terminy: 5"


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
    PanelImportu(okno, podglad).zatwierdz()
    assert len(okno.serwisy.transakcje.wszystkie()) == len(transakcje) + 8

    drugi = PanelImportu(okno, okno.serwisy.importer.przygotuj(WYCIAG, PROFIL_SKARBONKI, 2))
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
    assert "Brak kolumn" in formularz.blad_ogolny()
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


def test_panel_jest_tylko_jeden(okno):
    pierwszy = formularze.nowa_transakcja(okno, Wydatek)
    drugi = formularze.nowa_transakcja(okno, Przychod)
    assert not pierwszy.winfo_exists()
    assert okno.panel is drugi
    okno.pokaz_widok("Plan")
    assert okno.panel is None
    assert not drugi.winfo_exists()


def test_przelacznik_rodzaju_transakcji(okno):
    formularze.nowa_transakcja(okno, Wydatek)
    for nazwa, klucz in (("Przelew", "zrodlo"), ("Waluta", "waluta"), ("Przychód", "kategoria")):
        formularze._przelacznik(okno, "Wydatek").opcje[nazwa]()
        assert klucz in okno.panel._pola


def test_enter_zatwierdza_panel(okno, transakcje):
    formularz = formularze.nowa_transakcja(okno, Wydatek)
    formularz.ustaw("kwota", "5")
    formularz.ustaw("opis", "Woda")
    okno._zatwierdz_panel()
    assert len(okno.serwisy.transakcje.wszystkie()) == len(transakcje) + 1
    okno._zatwierdz_panel()
    assert len(okno.serwisy.transakcje.wszystkie()) == len(transakcje) + 1


def test_licznik_spraw(okno):
    okno.serwisy.budzety.ustaw(1, date.today(), Decimal("1"))
    okno.serwisy.transakcje.dodaj(Wydatek(date.today(), Decimal("5"), "Kawa", 1, 1))
    okno.odswiez()
    assert okno.pasek._pozycje["Plan"]._licznik.cget("text") == "1"


def test_lista_skraca_dlugie_opisy(okno):
    lista = okno.widok().tabela
    lista.wypelnij([Pozycja(1, ikony.DOM, "x" * 300, "y" * 300, "1 000,00 zł")])
    skrocony = lista._skroc("x" * 300, "tytul", 100)
    assert skrocony.endswith("…")
    assert lista._czcionki["tytul"].measure(skrocony) <= 100
    assert lista._skroc("Kawa", "tytul", 500) == "Kawa"


def test_pusty_pulpit_zacheca_do_dodania(baza, tmp_path, otworz):
    serwisy = utworz_serwisy(baza, tmp_path)
    dodaj_dane_startowe(serwisy)
    okno = otworz(serwisy)
    assert okno.widok()._pusty.winfo_manager() == "pack"
    wypelnij(formularze.nowa_transakcja(okno, Wydatek), kwota="5", opis="Woda")
    assert okno.widok()._pusty.winfo_manager() == ""


@pytest.mark.parametrize("ile", [1, 6, 40])
def test_pasek_przewijania_nie_zapetla_okna(okno, ile):
    ramka = Przewijana(okno)
    ramka.configure(height=120)
    ramka.place(x=0, y=0, relwidth=0.5)
    zmiany = []
    ramka._scrollbar.bind("<Map>", lambda _: zmiany.append(1))
    ramka._scrollbar.bind("<Unmap>", lambda _: zmiany.append(1))
    for i in range(ile):
        etykieta(ramka, f"Linia {i}").pack()
    okno.deiconify()
    for _ in range(50):
        okno.update()
    okno.withdraw()
    assert len(zmiany) < 10


@pytest.mark.parametrize(
    ("nazwa", "ikona"),
    [
        ("Jedzenie", ikony.JEDZENIE),
        ("TRANSPORT", ikony.AUTO),
        ("Wakacje w górach", ikony.SAMOLOT),
        ("Nieznane", ikony.METKA),
    ],
)
def test_ikona_kategorii(nazwa, ikona):
    assert ikony.dla_nazwy(nazwa) == ikona


def test_komunikaty_bez_okna(monkeypatch):
    pokazane = []
    monkeypatch.setattr(messagebox, "showinfo", lambda tytul, tekst, **k: pokazane.append(tekst))
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    z_ponowieniem(lambda: komunikaty.pokaz("Uwaga"))
    assert pokazane == ["Uwaga"]
    assert z_ponowieniem(lambda: komunikaty.zapytaj("Na pewno?")) is True
