"""Główna klasa interfejsu: stan aplikacji i drzewo menu."""

from skarbonka.config import NAZWA_APLIKACJI, SLOWO_ANULUJ
from skarbonka.models.transakcja import Przychod, Transakcja, Wydatek
from skarbonka.services import transakcje as serwis
from skarbonka.ui.menu import Menu, OpcjaMenu
from skarbonka.ui.wejscie import (
    potwierdz,
    wczytaj_date,
    wczytaj_kwote,
    wczytaj_numer,
    wczytaj_tekst,
)
from skarbonka.utils.formatowanie import formatuj_kwote


def pokaz_naglowek() -> None:
    """Wypisuje tytuł i krótką instrukcję."""
    tytul = f" {NAZWA_APLIKACJI} "
    print(tytul.center(60, "="))
    print(f"Słowo „{SLOWO_ANULUJ}” w dowolnym polu przerywa operację.")


class Aplikacja:
    """Przechowuje transakcje i łączy opcje menu z działaniami."""

    def __init__(self) -> None:
        self.transakcje: list[Transakcja] = []
        menu_transakcji = Menu(
            "Transakcje",
            [
                OpcjaMenu("Dodaj wydatek", lambda: self.dodaj(Wydatek)),
                OpcjaMenu("Dodaj przychód", lambda: self.dodaj(Przychod)),
                OpcjaMenu("Lista transakcji", self.pokaz_liste),
                OpcjaMenu("Usuń transakcję", self.usun),
            ],
        )
        menu_analiz = Menu(
            "Analizy",
            [OpcjaMenu("Saldo i sumy", self.pokaz_sumy)],
        )
        self.menu_glowne = Menu(
            "Menu główne",
            [
                OpcjaMenu("Transakcje", menu_transakcji.uruchom),
                OpcjaMenu("Analizy", menu_analiz.uruchom),
            ],
            powrot="Wyjście",
        )

    def uruchom(self) -> None:
        """Pokazuje nagłówek i oddaje sterowanie menu głównemu."""
        pokaz_naglowek()
        self.menu_glowne.uruchom()

    def dodaj(self, rodzaj: type[Transakcja]) -> None:
        """Wczytuje dane i dodaje transakcję podanego rodzaju."""
        kwota = wczytaj_kwote()
        data = wczytaj_date()
        opis = wczytaj_tekst("Opis")
        transakcja = rodzaj(data, kwota, opis)
        serwis.dodaj(self.transakcje, transakcja)
        print(f"  Dodano: {transakcja}")

    def pokaz_liste(self) -> None:
        """Wypisuje wszystkie transakcje od najnowszej."""
        if not self.transakcje:
            print("Brak transakcji.")
            return
        for transakcja in serwis.od_najnowszych(self.transakcje):
            print(transakcja)
        print(f"Razem: {len(self.transakcje)}")

    def usun(self) -> None:
        """Usuwa wybraną transakcję po potwierdzeniu."""
        self.pokaz_liste()
        if not self.transakcje:
            return
        transakcja = serwis.znajdz(self.transakcje, wczytaj_numer("Numer transakcji"))
        print(transakcja)
        if potwierdz("Na pewno usunąć?"):
            serwis.usun(self.transakcje, transakcja.id)
            print("  Usunięto.")
        else:
            print("  Nic nie usunięto.")

    def pokaz_sumy(self) -> None:
        """Wypisuje sumy przychodów i wydatków oraz saldo."""
        sumy = {
            "Przychody": serwis.suma_przychodow(self.transakcje),
            "Wydatki": serwis.suma_wydatkow(self.transakcje),
            "Saldo": serwis.saldo(self.transakcje),
        }
        for nazwa, kwota in sumy.items():
            print(f"{nazwa:<12} {formatuj_kwote(kwota):>16}")
