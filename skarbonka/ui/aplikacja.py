"""Główna klasa interfejsu: stan aplikacji i drzewo menu."""

from skarbonka.config import NAZWA_APLIKACJI, SLOWO_ANULUJ
from skarbonka.models.transakcja import Przychod, Transakcja, Wydatek
from skarbonka.services.transakcje import saldo, suma_przychodow, suma_wydatkow
from skarbonka.ui.menu import Menu, OpcjaMenu
from skarbonka.ui.wejscie import wczytaj_date, wczytaj_kwote, wczytaj_tekst
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
        self.transakcje.append(transakcja)
        print(f"  Dodano: {transakcja}")

    def pokaz_sumy(self) -> None:
        """Wypisuje sumy przychodów i wydatków oraz saldo."""
        sumy = {
            "Przychody": suma_przychodow(self.transakcje),
            "Wydatki": suma_wydatkow(self.transakcje),
            "Saldo": saldo(self.transakcje),
        }
        for nazwa, kwota in sumy.items():
            print(f"{nazwa:<12} {formatuj_kwote(kwota):>16}")
