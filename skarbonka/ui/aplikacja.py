"""Przebieg działania aplikacji."""

from skarbonka.config import NAZWA_APLIKACJI, SLOWO_ANULUJ
from skarbonka.models.transakcja import Przychod, Transakcja, Wydatek
from skarbonka.services.transakcje import saldo, suma_przychodow, suma_wydatkow
from skarbonka.ui.wejscie import (
    potwierdz,
    wczytaj_date,
    wczytaj_kwote,
    wczytaj_tekst,
    wczytaj_wybor,
)
from skarbonka.utils.formatowanie import formatuj_kwote
from skarbonka.wyjatki import AnulowanoOperacje


def pokaz_naglowek() -> None:
    """Wypisuje tytuł i krótką instrukcję."""
    tytul = f" {NAZWA_APLIKACJI} "
    print(tytul.center(60, "="))
    print(f"Wpisz transakcje. Słowo „{SLOWO_ANULUJ}” przerywa wpisywanie.\n")


def wczytaj_transakcje() -> Transakcja:
    """Pyta o wszystkie pola i tworzy wydatek albo przychód."""
    rodzaj = wczytaj_wybor("Rodzaj: w (wydatek) / p (przychód)", ("w", "p"))
    kwota = wczytaj_kwote()
    data = wczytaj_date()
    opis = wczytaj_tekst("Opis")
    if rodzaj == "w":
        return Wydatek(data, kwota, opis)
    return Przychod(data, kwota, opis)


def pokaz_podsumowanie(transakcje: list[Transakcja]) -> None:
    """Wypisuje transakcje od najstarszej oraz sumy i saldo."""
    print(f"\nTransakcje: {len(transakcje)}")
    for numer, transakcja in enumerate(sorted(transakcje, key=lambda t: t.data), start=1):
        print(f"{numer:>3}. {transakcja}")

    sumy = {
        "Przychody": suma_przychodow(transakcje),
        "Wydatki": suma_wydatkow(transakcje),
        "Saldo": saldo(transakcje),
    }
    print()
    for nazwa, kwota in sumy.items():
        print(f"{nazwa:<10} {formatuj_kwote(kwota):>16}")


def uruchom() -> None:
    """Wczytuje transakcje, a na koniec pokazuje podsumowanie."""
    pokaz_naglowek()
    transakcje: list[Transakcja] = []
    try:
        while True:
            transakcje.append(wczytaj_transakcje())
            print(f"  Dodano: {transakcje[-1]}")
            if not potwierdz("\nDodać kolejną transakcję?"):
                break
    except AnulowanoOperacje as blad:
        print(f"  {blad}")

    if transakcje:
        pokaz_podsumowanie(transakcje)
    else:
        print("Nie dodano żadnej transakcji.")
