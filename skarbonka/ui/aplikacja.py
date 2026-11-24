"""Główna klasa interfejsu: drzewo menu."""

from dataclasses import replace
from decimal import Decimal

from skarbonka.config import NAZWA_APLIKACJI, SLOWO_ANULUJ
from skarbonka.models.enums import TypKonta
from skarbonka.models.transakcja import Przelew, Przychod, Transakcja, Wydatek
from skarbonka.services import analizy
from skarbonka.services import transakcje as obliczenia
from skarbonka.services.zestaw import utworz_serwisy
from skarbonka.ui.menu import Menu, OpcjaMenu
from skarbonka.ui.wejscie import (
    potwierdz,
    wczytaj_date,
    wczytaj_date_opcjonalna,
    wczytaj_fraze,
    wczytaj_kwote,
    wczytaj_miesiac,
    wczytaj_nazwe,
    wczytaj_numer,
    wczytaj_saldo,
    wczytaj_tekst,
    wybierz,
    wybierz_lub_wszystkie,
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
    """Łączy opcje menu z działaniami."""

    def __init__(self) -> None:
        serwisy = utworz_serwisy()
        self.transakcje = serwisy.transakcje
        self.konta = serwisy.konta
        self.kategorie = serwisy.kategorie
        menu_transakcji = Menu(
            "Transakcje",
            [
                OpcjaMenu("Dodaj wydatek", lambda: self.dodaj(Wydatek)),
                OpcjaMenu("Dodaj przychód", lambda: self.dodaj(Przychod)),
                OpcjaMenu("Przelew między kontami", self.dodaj_przelew),
                OpcjaMenu("Lista transakcji", self.pokaz_liste),
                OpcjaMenu("Szukaj i filtruj", self.szukaj),
                OpcjaMenu("Edytuj transakcję", self.edytuj),
                OpcjaMenu("Usuń transakcję", self.usun),
            ],
        )
        menu_analiz = Menu(
            "Analizy",
            [
                OpcjaMenu("Saldo i sumy", self.pokaz_sumy),
                OpcjaMenu("Podsumowanie miesiąca", self.pokaz_miesiac),
                OpcjaMenu("Wydatki według kategorii", self.pokaz_kategorie_wydatkow),
                OpcjaMenu("Trend 6 miesięcy", self.pokaz_trend),
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
        konto = wybierz("Konto", self.konta.wszystkie())
        kwota = wczytaj_kwote()
        data = wczytaj_date()
        opis = wczytaj_tekst("Opis")
        kategoria = wybierz("Kategoria", self.kategorie.pasujace(rodzaj))
        self._zapisz(rodzaj(data, kwota, opis, konto.id, kategoria.id))

    def dodaj_przelew(self) -> None:
        """Wczytuje dane i dodaje przelew między dwoma kontami."""
        if len(self.konta.wszystkie()) < 2:
            print("Przelew wymaga co najmniej dwóch kont.")
            return
        zrodlo = wybierz("Z konta", self.konta.wszystkie())
        cel = wybierz("Na konto", [k for k in self.konta.wszystkie() if k.id != zrodlo.id])
        kwota = wczytaj_kwote()
        data = wczytaj_date()
        opis = f"{zrodlo.nazwa} -> {cel.nazwa}"
        self._zapisz(Przelew(data, kwota, opis, zrodlo.id, konto_docelowe_id=cel.id))

    def _zapisz(self, transakcja: Transakcja) -> None:
        """Dopisuje transakcję i potwierdza to na ekranie."""
        self.transakcje.dodaj(transakcja)
        print(f"  Dodano: {transakcja}")

    def pokaz_liste(self) -> None:
        """Wypisuje wszystkie transakcje od najnowszej."""
        self._wypisz(obliczenia.posortuj(self.transakcje.wszystkie()))

    def szukaj(self) -> None:
        """Wypisuje transakcje spełniające podane warunki wraz z sumami."""
        od = wczytaj_date_opcjonalna("Od dnia")
        do = wczytaj_date_opcjonalna("Do dnia")
        konto = wybierz_lub_wszystkie("Konto", self.konta.wszystkie())
        kategoria = wybierz_lub_wszystkie("Kategoria", self.kategorie.wszystkie())
        fraza = wczytaj_fraze("Fragment opisu")
        sposob = wybierz("Kolejność", list(obliczenia.SORTOWANIA), "od najnowszych")
        wybrane = self.transakcje.filtruj(
            od,
            do,
            konto_id=konto.id if konto else None,
            kategoria_id=kategoria.id if kategoria else None,
            fraza=fraza,
        )
        self._wypisz(obliczenia.posortuj(wybrane, sposob))
        if wybrane:
            pokaz_kwoty(
                {
                    "Przychody": obliczenia.suma_przychodow(wybrane),
                    "Wydatki": obliczenia.suma_wydatkow(wybrane),
                }
            )

    def _wypisz(self, transakcje: list[Transakcja]) -> None:
        """Wypisuje transakcje z nazwami kont i kategorii."""
        if not transakcje:
            print("Brak transakcji.")
            return
        nazwy_kont = self.konta.nazwy()
        nazwy_kategorii = self.kategorie.nazwy()
        for transakcja in transakcje:
            konto = nazwy_kont[transakcja.konto_id]
            kategoria = nazwy_kategorii.get(transakcja.kategoria_id, "-")
            print(f"{transakcja}  [{konto} | {kategoria}]")
        print(f"Razem: {len(transakcje)}")

    def edytuj(self) -> None:
        """Zmienia wybraną transakcję. Enter zostawia dotychczasową wartość."""
        self.pokaz_liste()
        if not self.transakcje.wszystkie():
            return
        stara = self.transakcje.pobierz(wczytaj_numer("Numer transakcji"))
        zmiany = {
            "kwota": wczytaj_kwote(domyslna=stara.kwota),
            "data": wczytaj_date(domyslna=stara.data),
            "opis": wczytaj_tekst("Opis", domyslna=stara.opis),
        }
        pasujace = self.kategorie.pasujace(type(stara))
        if pasujace:
            obecna = self.kategorie.pobierz(stara.kategoria_id)
            zmiany["kategoria_id"] = wybierz("Kategoria", pasujace, obecna).id
            obecne = self.konta.pobierz(stara.konto_id)
            zmiany["konto_id"] = wybierz("Konto", self.konta.wszystkie(), obecne).id
        nowa = replace(stara, **zmiany)
        self.transakcje.zmien(nowa)
        print(f"  Zmieniono: {nowa}")

    def usun(self) -> None:
        """Usuwa wybraną transakcję po potwierdzeniu."""
        self.pokaz_liste()
        if not self.transakcje.wszystkie():
            return
        transakcja = self.transakcje.pobierz(wczytaj_numer("Numer transakcji"))
        print(transakcja)
        if potwierdz("Na pewno usunąć?"):
            self.transakcje.usun(transakcja)
            print("  Usunięto.")
        else:
            print("  Nic nie usunięto.")

    def pokaz_sumy(self) -> None:
        """Wypisuje sumy przychodów i wydatków oraz salda kont."""
        sumy = {
            "Przychody": obliczenia.suma_przychodow(self.transakcje.wszystkie()),
            "Wydatki": obliczenia.suma_wydatkow(self.transakcje.wszystkie()),
            "Bilans": obliczenia.bilans(self.transakcje.wszystkie()),
        }
        pokaz_kwoty(sumy)
        print()
        self.pokaz_konta()

    def pokaz_konta(self) -> None:
        """Wypisuje konta z saldami i saldo łączne."""
        for konto in self.konta.wszystkie():
            kwota = formatuj_kwote(self.konta.saldo(konto.id))
            print(f"{str(konto):<40} {kwota:>16}")
        razem = formatuj_kwote(self.konta.saldo())
        print(f"{'Razem':<40} {razem:>16}")

    def dodaj_konto(self) -> None:
        """Wczytuje dane i dodaje konto."""
        nazwa = wczytaj_nazwe("Nazwa konta", self.konta.sprawdz_nazwe)
        typ = wybierz("Typ konta", list(TypKonta))
        konto = self.konta.dodaj(nazwa, typ, wczytaj_saldo())
        print(f"  Dodano: {konto}")

    def usun_konto(self) -> None:
        """Usuwa wybrane konto po potwierdzeniu."""
        konto = wybierz("Konto do usunięcia", self.konta.wszystkie())
        if potwierdz(f"Na pewno usunąć „{konto.nazwa}”?"):
            self.konta.usun(konto)
            print("  Usunięto.")

    def pokaz_kategorie(self) -> None:
        """Wypisuje kategorie w podziale na wydatki i przychody."""
        for tytul, rodzaj in (("Wydatki", Wydatek), ("Przychody", Przychod)):
            nazwy = [k.nazwa for k in self.kategorie.pasujace(rodzaj)]
            print(f"{tytul}: {', '.join(nazwy) or 'brak'}")

    def dodaj_kategorie(self) -> None:
        """Wczytuje dane i dodaje kategorię."""
        nazwa = wczytaj_nazwe("Nazwa kategorii", self.kategorie.sprawdz_nazwe)
        czy_wydatek = potwierdz("Czy to kategoria wydatków?")
        self.kategorie.dodaj(nazwa, czy_wydatek)
        print(f"  Dodano: {nazwa}")

    def usun_kategorie(self) -> None:
        """Usuwa wybraną kategorię po potwierdzeniu."""
        kategoria = wybierz("Kategoria do usunięcia", self.kategorie.wszystkie())
        if potwierdz(f"Na pewno usunąć „{kategoria.nazwa}”?"):
            self.kategorie.usun(kategoria)
            print("  Usunięto.")

    def pokaz_miesiac(self) -> None:
        """Wypisuje podsumowanie wybranego miesiąca."""
        miesiac = wczytaj_miesiac()
        wybrane = analizy.z_miesiaca(self.transakcje.wszystkie(), miesiac)
        print()
        print(f"{formatuj_miesiac(miesiac).capitalize()}, transakcje: {len(wybrane)}")
        podsumowanie = analizy.podsumowanie_miesiaca(self.transakcje.wszystkie(), miesiac)
        pokaz_kwoty(podsumowanie)
        stopa = analizy.stopa_oszczednosci(podsumowanie["Przychody"], podsumowanie["Bilans"])
        if stopa is not None:
            print(f"{'Oszczędności':<12} {formatuj_procent(stopa):>16}")

    def pokaz_kategorie_wydatkow(self) -> None:
        """Wypisuje kategorie miesiąca z kwotą, procentem i paskiem."""
        wybrane = analizy.z_miesiaca(self.transakcje.wszystkie(), wczytaj_miesiac())
        kwoty = analizy.wydatki_wg_kategorii(wybrane, self.kategorie.wszystkie())
        if not kwoty:
            print("Brak wydatków w tym miesiącu.")
            return
        procenty = analizy.udzialy(kwoty)
        for nazwa, kwota in kwoty.items():
            pasek = "█" * max(1, round(procenty[nazwa] / 5))
            procent = formatuj_procent(procenty[nazwa])
            print(f"{nazwa:<25} {formatuj_kwote(kwota):>16} {procent:>7}  {pasek}")

    def pokaz_trend(self) -> None:
        """Wypisuje przychody, wydatki i bilans ostatnich miesięcy."""
        kolumny = ("Przychody", "Wydatki", "Bilans")
        print(f"{'Miesiąc':<18}" + "".join(f"{nazwa:>18}" for nazwa in kolumny))
        for miesiac, sumy in analizy.trend(self.transakcje.wszystkie()):
            kwoty = "".join(f"{formatuj_kwote(sumy[nazwa]):>18}" for nazwa in kolumny)
            print(f"{formatuj_miesiac(miesiac):<18}{kwoty}")

    def pokaz_najwieksze(self) -> None:
        """Wypisuje pięć największych wydatków."""
        wydatki = analizy.najwieksze_wydatki(self.transakcje.wszystkie())
        if not wydatki:
            print("Brak wydatków.")
        for miejsce, wydatek in enumerate(wydatki, start=1):
            print(f"{miejsce}. {wydatek}")
