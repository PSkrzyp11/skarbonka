"""Odczyt i zapis plików CSV."""

import csv
from collections.abc import Iterable, Iterator
from pathlib import Path

from skarbonka.models.importy import ProfilCSV
from skarbonka.wyjatki import BladPliku, UszkodzonyPlik

SEPARATOR = ";"
KODOWANIE = "utf-8-sig"


def zapisz_csv(sciezka: Path, naglowki: list[str], wiersze: Iterable[list[str]]) -> None:
    """Zapisuje tabelę w układzie, który polski Excel otwiera bez pytań."""
    try:
        sciezka.parent.mkdir(parents=True, exist_ok=True)
        with open(sciezka, "w", encoding=KODOWANIE, newline="") as plik:
            zapis = csv.writer(plik, delimiter=SEPARATOR)
            zapis.writerow(naglowki)
            zapis.writerows(wiersze)
    except PermissionError as blad:
        raise BladPliku(
            f"Brak dostępu do {sciezka}. Plik może być otwarty w innym programie."
        ) from blad
    except (OSError, ValueError) as blad:
        raise BladPliku(f"Nie można zapisać pliku {sciezka}: {blad}") from blad


def czytaj_naglowki(sciezka: Path, profil: ProfilCSV) -> list[str]:
    """Zwraca nazwy kolumn z pliku."""
    return next(_czytaj(sciezka, profil))[1]


def czytaj_wiersze(sciezka: Path, profil: ProfilCSV) -> Iterator[tuple[int, dict[str, str]]]:
    """Generator: oddaje numer linii i słownik kolumna -> wartość.

    Wielkość liter w nazwach kolumn nie ma znaczenia.
    """
    linie = _czytaj(sciezka, profil)
    naglowki = [nazwa.casefold() for nazwa in next(linie)[1]]
    brakujace = [k for k in profil.wymagane_kolumny if k.casefold() not in naglowki]
    if brakujace:
        raise UszkodzonyPlik(
            f"Brak kolumn: {', '.join(brakujace)}. Kolumny w pliku: {', '.join(naglowki)}."
        )
    for numer, komorki in linie:
        if not any(komorki):
            continue
        yield numer, dict(zip(naglowki, komorki))


def _czytaj(sciezka: Path, profil: ProfilCSV) -> Iterator[tuple[int, list[str]]]:
    """Generator: oddaje numer i komórki kolejnych linii, zaczynając od nagłówków."""
    try:
        with open(sciezka, encoding=profil.kodowanie, newline="") as plik:
            for _ in range(profil.pomin_linie):
                plik.readline()
            odczyt = csv.reader(plik, delimiter=profil.separator)
            pusty = True
            for komorki in odczyt:
                pusty = False
                yield profil.pomin_linie + odczyt.line_num, list(map(str.strip, komorki))
            if pusty:
                raise UszkodzonyPlik(f"Plik {sciezka.name} jest pusty.")
    except FileNotFoundError as blad:
        raise BladPliku(f"Nie ma pliku {sciezka}.") from blad
    except PermissionError as blad:
        raise BladPliku(f"Brak dostępu do {sciezka}.") from blad
    except UnicodeDecodeError as blad:
        raise UszkodzonyPlik(
            f"Plik {sciezka.name} nie ma kodowania {profil.kodowanie}. Zmień profil CSV."
        ) from blad
    except csv.Error as blad:
        raise UszkodzonyPlik(f"Plik {sciezka.name} nie jest poprawnym CSV: {blad}.") from blad
    except (OSError, LookupError, ValueError, TypeError) as blad:
        raise BladPliku(f"Nie można odczytać pliku {sciezka}: {blad}") from blad
