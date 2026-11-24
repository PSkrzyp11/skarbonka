"""Główna klasa interfejsu: stan aplikacji i drzewo menu."""

from decimal import Decimal

from skarbonka.config import MAKS_DLUGOSC_NAZWY, NAZWA_APLIKACJI, SLOWO_ANULUJ
from skarbonka.models.enums import TypKonta
from skarbonka.models.kategoria import Kategoria
from skarbonka.models.konto import Konto
from skarbonka.models.transakcja import Przelew, Przychod, Transakcja, Wydatek
from skarbonka.services import analizy, rekordy
from skarbonka.services import kategorie as serwis_kategorii
from skarbonka.services import konta as serwis_kont
from skarbonka.services import transakcje as serwis
from skarbonka.ui.menu import Menu, OpcjaMenu
from skarbonka.ui.wejscie import (
    potwierdz,
    wczytaj_date,
    wczytaj_kwote,
    wczytaj_miesiac,
    wczytaj_numer,
    wczytaj_saldo,
    wczytaj_tekst,
    wybierz,
)
from skarbonka.utils.formatowanie import formatuj_kwote, formatuj_miesiac, formatuj_procent


def pokaz_naglowek() -> None:
    """Wypisuje tytuł i krótką instrukcję."""
    tytul = f" {NAZWA_APLIKACJI} "
    print(tytul.center(60, "="))
    print(f"Słowo „{SLOWO_ANULUJ}” w dowolnym polu przerywa operację.")


def pokaz_kwoty(kwoty: dict[str, Decimal]) -> None:
    """Wypisuje nazwy i kwoty w dwóch kolumnach."""
    for nazwa, kwota in kwoty.items():
        print(f"{nazwa:<12} {formatuj_kwote(kwota):>16}")


class Aplikacja:
    """Przechowuje transakcje i łączy opcje menu z działaniami."""

    def __init__(self) -> None:
        self.konta: list[Konto] = []
        self.kategorie: list[Kategoria] = serwis_kategorii.domyslne_kategorie()
        self.transakcje: list[Transakcja] = []
        rekordy.dodaj(self.konta, Konto("Portfel", TypKonta.GOTOWKA))
        menu_transakcji = Menu(
            "Transakcje",
            [
                OpcjaMenu("Dodaj wydatek", lambda: self.dodaj(Wydatek)),
                OpcjaMenu("Dodaj przychód", lambda: self.dodaj(Przychod)),
                OpcjaMenu("Przelew między kontami", self.dodaj_przelew),
                OpcjaMenu("Lista transakcji", self.pokaz_liste),
                OpcjaMenu("Usuń transakcję", self.usun),
            ],
        )
        menu_analiz = Menu(
            "Analizy",
            [
                OpcjaMenu("Saldo i sumy", self.pokaz_sumy),
                OpcjaMenu("Podsumowanie miesiąca", self.pokaz_miesiac),
                OpcjaMenu("Największe wydatki", self.pokaz_najwieksze),
            ],
        )
        menu_kont = Menu(
            "Konta",
            [
                OpcjaMenu("Lista kont", self.pokaz_konta),
                OpcjaMenu("Dodaj konto", self.dodaj_konto),
                OpcjaMenu("Usuń konto", self.usun_konto),
            ],
        )
        menu_kategorii = Menu(
            "Kategorie",
            [
                OpcjaMenu("Lista kategorii", self.pokaz_kategorie),
                OpcjaMenu("Dodaj kategorię", self.dodaj_kategorie),
                OpcjaMenu("Usuń kategorię", self.usun_kategorie),
            ],
        )
        menu_ustawien = Menu(
            "Ustawienia",
            [
                OpcjaMenu("Konta", menu_kont.uruchom),
                OpcjaMenu("Kategorie", menu_kategorii.uruchom),
            ],
        )
        self.menu_glowne = Menu(
            "Menu główne",
            [
                OpcjaMenu("Transakcje", menu_transakcji.uruchom),
                OpcjaMenu("Analizy", menu_analiz.uruchom),
                OpcjaMenu("Ustawienia", menu_ustawien.uruchom),
            ],
            powrot="Wyjście",
        )

    def uruchom(self) -> None:
        """Pokazuje nagłówek i oddaje sterowanie menu głównemu."""
        pokaz_naglowek()
        self.menu_glowne.uruchom()

    def dodaj(self, rodzaj: type[Transakcja]) -> None:
        """Wczytuje dane i dodaje transakcję podanego rodzaju."""
        konto = wybierz("Konto", self.konta)
        kwota = wczytaj_kwote()
        data = wczytaj_date()
        opis = wczytaj_tekst("Opis")
        kategoria = wybierz("Kategoria", serwis_kategorii.pasujace(self.kategorie, rodzaj))
        self._zapisz(rodzaj(data, kwota, opis, konto.id, kategoria.id))

    def dodaj_przelew(self) -> None:
        """Wczytuje dane i dodaje przelew między dwoma kontami."""
        if len(self.konta) < 2:
            print("Przelew wymaga co najmniej dwóch kont.")
            return
        zrodlo = wybierz("Z konta", self.konta)
        cel = wybierz("Na konto", [k for k in self.konta if k is not zrodlo])
        kwota = wczytaj_kwote()
        data = wczytaj_date()
        opis = f"{zrodlo.nazwa} -> {cel.nazwa}"
        self._zapisz(Przelew(data, kwota, opis, zrodlo.id, konto_docelowe_id=cel.id))

    def _zapisz(self, transakcja: Transakcja) -> None:
        """Dopisuje transakcję i potwierdza to na ekranie."""
        rekordy.dodaj(self.transakcje, transakcja)
        print(f"  Dodano: {transakcja}")

    def pokaz_liste(self) -> None:
        """Wypisuje wszystkie transakcje od najnowszej."""
        if not self.transakcje:
            print("Brak transakcji.")
            return
        nazwy_kont = {k.id: k.nazwa for k in self.konta}
        nazwy_kategorii = {k.id: k.nazwa for k in self.kategorie}
        for transakcja in serwis.od_najnowszych(self.transakcje):
            konto = nazwy_kont[transakcja.konto_id]
            kategoria = nazwy_kategorii.get(transakcja.kategoria_id, "-")
            print(f"{transakcja}  [{konto} | {kategoria}]")
        print(f"Razem: {len(self.transakcje)}")

    def usun(self) -> None:
        """Usuwa wybraną transakcję po potwierdzeniu."""
        self.pokaz_liste()
        if not self.transakcje:
            return
        transakcja = rekordy.znajdz(self.transakcje, wczytaj_numer("Numer transakcji"))
        print(transakcja)
        if potwierdz("Na pewno usunąć?"):
            rekordy.usun(self.transakcje, transakcja.id)
            print("  Usunięto.")
        else:
            print("  Nic nie usunięto.")

    def pokaz_sumy(self) -> None:
        """Wypisuje sumy przychodów i wydatków oraz salda kont."""
        sumy = {
            "Przychody": serwis.suma_przychodow(self.transakcje),
            "Wydatki": serwis.suma_wydatkow(self.transakcje),
            "Bilans": serwis.bilans(self.transakcje),
        }
        pokaz_kwoty(sumy)
        print()
        self.pokaz_konta()

    def pokaz_konta(self) -> None:
        """Wypisuje konta z saldami i saldo łączne."""
        for konto in self.konta:
            kwota = formatuj_kwote(serwis_kont.saldo(self.konta, self.transakcje, konto.id))
            print(f"{str(konto):<40} {kwota:>16}")
        razem = formatuj_kwote(serwis_kont.saldo(self.konta, self.transakcje))
        print(f"{'Razem':<40} {razem:>16}")

    def dodaj_konto(self) -> None:
        """Wczytuje dane i dodaje konto."""
        nazwa = wczytaj_tekst("Nazwa konta", MAKS_DLUGOSC_NAZWY)
        rekordy.sprawdz_nazwe(self.konta, nazwa)
        typ = wybierz("Typ konta", list(TypKonta))
        konto = Konto(nazwa, typ, wczytaj_saldo())
        rekordy.dodaj(self.konta, konto)
        print(f"  Dodano: {konto}")

    def usun_konto(self) -> None:
        """Usuwa wybrane konto po potwierdzeniu."""
        konto = wybierz("Konto do usunięcia", self.konta)
        if potwierdz(f"Na pewno usunąć „{konto.nazwa}”?"):
            serwis_kont.usun_konto(self.konta, konto, self.transakcje)
            print("  Usunięto.")

    def pokaz_kategorie(self) -> None:
        """Wypisuje kategorie w podziale na wydatki i przychody."""
        for tytul, rodzaj in (("Wydatki", Wydatek), ("Przychody", Przychod)):
            nazwy = [k.nazwa for k in serwis_kategorii.pasujace(self.kategorie, rodzaj)]
            print(f"{tytul}: {', '.join(nazwy) or 'brak'}")

    def dodaj_kategorie(self) -> None:
        """Wczytuje dane i dodaje kategorię."""
        nazwa = wczytaj_tekst("Nazwa kategorii", MAKS_DLUGOSC_NAZWY)
        rekordy.sprawdz_nazwe(self.kategorie, nazwa)
        czy_wydatek = potwierdz("Czy to kategoria wydatków?")
        rekordy.dodaj(self.kategorie, Kategoria(nazwa, czy_wydatek))
        print(f"  Dodano: {nazwa}")

    def usun_kategorie(self) -> None:
        """Usuwa wybraną kategorię po potwierdzeniu."""
        kategoria = wybierz("Kategoria do usunięcia", self.kategorie)
        if potwierdz(f"Na pewno usunąć „{kategoria.nazwa}”?"):
            serwis_kategorii.usun_kategorie(self.kategorie, kategoria, self.transakcje)
            print("  Usunięto.")

    def pokaz_miesiac(self) -> None:
        """Wypisuje podsumowanie wybranego miesiąca."""
        miesiac = wczytaj_miesiac()
        wybrane = analizy.z_miesiaca(self.transakcje, miesiac)
        print()
        print(f"{formatuj_miesiac(miesiac).capitalize()}, transakcje: {len(wybrane)}")
        podsumowanie = analizy.podsumowanie_miesiaca(self.transakcje, miesiac)
        pokaz_kwoty(podsumowanie)
        stopa = analizy.stopa_oszczednosci(podsumowanie["Przychody"], podsumowanie["Bilans"])
        if stopa is not None:
            print(f"{'Oszczędności':<12} {formatuj_procent(stopa):>16}")

    def pokaz_najwieksze(self) -> None:
        """Wypisuje pięć największych wydatków."""
        wydatki = analizy.najwieksze_wydatki(self.transakcje)
        if not wydatki:
            print("Brak wydatków.")
        for miejsce, wydatek in enumerate(wydatki, start=1):
            print(f"{miejsce}. {wydatek}")
