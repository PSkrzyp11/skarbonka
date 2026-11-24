"""Stałe używane w całej aplikacji."""

from pathlib import Path

NAZWA_APLIKACJI = "Skarbonka"

KATALOG_PROJEKTU = Path(__file__).resolve().parent.parent
KATALOG_DANYCH = KATALOG_PROJEKTU / "dane"
PLIK_BAZY = KATALOG_DANYCH / "skarbonka.db"
PLIK_LOGU = KATALOG_DANYCH / "logi" / "skarbonka.log"

SLOWO_ANULUJ = "anuluj"

MAKS_DLUGOSC_OPISU = 60
MAKS_DLUGOSC_NAZWY = 25

ROZMIAR_STRONY = 20

KATEGORIE_WYDATKOW = (
    "Jedzenie", "Mieszkanie", "Transport", "Zdrowie", "Rozrywka", "Ubrania", "Inne wydatki",
)
KATEGORIE_PRZYCHODOW = ("Wynagrodzenie", "Inne przychody")
