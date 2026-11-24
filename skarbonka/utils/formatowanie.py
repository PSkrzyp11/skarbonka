"""Zamiana wartości na tekst w polskim zapisie."""

from datetime import date, timedelta
from decimal import Decimal

NAZWY_MIESIECY = (
    "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
    "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień",
)
MIESIACE_DOPELNIACZ = (
    "stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
    "lipca", "sierpnia", "września", "października", "listopada", "grudnia",
)
DNI_TYGODNIA = (
    "poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela",
)


def formatuj_kwote(kwota: Decimal, jednostka: str = "zł") -> str:
    """Zwraca kwotę w postaci „1 234,50 zł”."""
    return f"{kwota:,.2f}".replace(",", " ").replace(".", ",") + f" {jednostka}"


def formatuj_kurs(kurs: Decimal) -> str:
    """Zwraca kurs w postaci „4,2512 zł”."""
    return f"{kurs:.4f} zł".replace(".", ",")


def formatuj_date(dzien: date) -> str:
    """Zwraca datę w postaci „24.11.2026”."""
    return f"{dzien:%d.%m.%Y}"


def formatuj_dzien(dzien: date, dzis: date | None = None, z_wzgledna: bool = True) -> str:
    """Zwraca dzień słownie: „Dziś”, „Wczoraj” albo „Sobota, 21 listopada”.

    Rok pojawia się tylko wtedy, gdy jest inny niż bieżący.
    """
    dzis = dzis or date.today()
    if z_wzgledna and dzien == dzis:
        return "Dziś"
    if z_wzgledna and dzien == dzis - timedelta(days=1):
        return "Wczoraj"
    nazwa = DNI_TYGODNIA[dzien.weekday()].capitalize()
    rok = "" if dzien.year == dzis.year else f" {dzien.year}"
    return f"{nazwa}, {dzien.day} {MIESIACE_DOPELNIACZ[dzien.month - 1]}{rok}"


def formatuj_miesiac(dzien: date) -> str:
    """Zwraca miesiąc w postaci „listopad 2026”."""
    return f"{NAZWY_MIESIECY[dzien.month - 1]} {dzien.year}"


def formatuj_procent(wartosc: float) -> str:
    """Zwraca procent w postaci „84,5%”."""
    return f"{wartosc:.1f}%".replace(".", ",")
