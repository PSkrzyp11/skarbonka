"""Zapis plików CSV."""

import csv
from collections.abc import Iterable
from pathlib import Path

from skarbonka.wyjatki import BladPliku

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
