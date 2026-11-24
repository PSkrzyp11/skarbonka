"""Odczyt i zapis plików JSON."""

import json
from pathlib import Path
from typing import Any

from skarbonka.wyjatki import BladPliku, UszkodzonyPlik


def wczytaj_json(sciezka: Path) -> Any:
    """Zwraca zawartość pliku JSON."""
    try:
        with open(sciezka, encoding="utf-8") as plik:
            return json.load(plik)
    except FileNotFoundError as blad:
        raise BladPliku(f"Nie ma pliku {sciezka}.") from blad
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as blad:
        raise UszkodzonyPlik(f"Plik {sciezka} nie jest poprawnym plikiem JSON.") from blad
    except (OSError, ValueError) as blad:
        raise BladPliku(f"Nie można odczytać pliku {sciezka}: {blad}") from blad


def zapisz_json(sciezka: Path, dane: Any) -> None:
    """Zapisuje dane do pliku JSON.

    Najpierw powstaje plik tymczasowy, więc przerwany zapis nie niszczy
    poprzedniej wersji.
    """
    tymczasowy = sciezka.with_name(sciezka.name + ".tmp")
    try:
        sciezka.parent.mkdir(parents=True, exist_ok=True)
        with open(tymczasowy, "w", encoding="utf-8") as plik:
            json.dump(dane, plik, ensure_ascii=False, indent=2)
        tymczasowy.replace(sciezka)
    except (OSError, ValueError) as blad:
        raise BladPliku(f"Nie można zapisać pliku {sciezka}: {blad}") from blad
