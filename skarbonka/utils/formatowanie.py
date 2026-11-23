"""Zamiana wartości na tekst w polskim zapisie."""

from datetime import date
from decimal import Decimal

NAZWY_MIESIECY = (
    "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
    "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień",
)


def formatuj_kwote(kwota: Decimal, ze_znakiem: bool = False) -> str:
    """Zwraca kwotę w postaci „1 234,50 zł”."""
    znak = "+" if ze_znakiem else ""
    tekst = f"{kwota:{znak},.2f}"
    return tekst.replace(",", " ").replace(".", ",") + " zł"


def formatuj_date(dzien: date) -> str:
    """Zwraca datę w postaci „24.11.2026”."""
    return f"{dzien:%d.%m.%Y}"


def formatuj_miesiac(dzien: date) -> str:
    """Zwraca miesiąc w postaci „listopad 2026”."""
    return f"{NAZWY_MIESIECY[dzien.month - 1]} {dzien.year}"


def formatuj_procent(wartosc: float) -> str:
    """Zwraca procent w postaci „84,5%”."""
    return f"{wartosc:.1f}%".replace(".", ",")
