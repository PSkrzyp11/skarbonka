"""Zamiana wartości na tekst w polskim zapisie."""

from datetime import date
from decimal import Decimal


def formatuj_kwote(kwota: Decimal, ze_znakiem: bool = False) -> str:
    """Zwraca kwotę w postaci „1 234,50 zł”."""
    znak = "+" if ze_znakiem else ""
    tekst = f"{kwota:{znak},.2f}"
    return tekst.replace(",", " ").replace(".", ",") + " zł"


def formatuj_date(dzien: date) -> str:
    """Zwraca datę w postaci „24.11.2026”."""
    return f"{dzien:%d.%m.%Y}"
