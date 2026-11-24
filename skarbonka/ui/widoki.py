"""Wypisywanie danych na ekran."""

from datetime import date
from decimal import Decimal

from skarbonka.config import NAZWA_APLIKACJI, SLOWO_ANULUJ
from skarbonka.models.konto import Konto
from skarbonka.models.transakcja import Transakcja
from skarbonka.utils.formatowanie import formatuj_kwote, formatuj_miesiac, formatuj_procent


def pokaz_naglowek() -> None:
    """Wypisuje tytuł i krótką instrukcję."""
    tytul = f" {NAZWA_APLIKACJI} "
    print(tytul.center(60, "="))
    print(f"Słowo „{SLOWO_ANULUJ}” w dowolnym polu przerywa operację.")


def sukces(tekst: str) -> None:
    """Wypisuje potwierdzenie wykonanej operacji."""
    print(f"  {tekst}")


def blad(tekst: str) -> None:
    """Wypisuje komunikat o błędzie."""
    print(f"  ! {tekst}")


def pokaz_kwoty(kwoty: dict[str, Decimal]) -> None:
    """Wypisuje nazwy i kwoty w dwóch kolumnach."""
    for nazwa, kwota in kwoty.items():
        print(f"{nazwa:<12} {formatuj_kwote(kwota):>16}")


def pokaz_transakcje(
    transakcje: list[Transakcja], nazwy_kont: dict[int, str], nazwy_kategorii: dict[int, str]
) -> None:
    """Wypisuje transakcje z nazwami kont i kategorii."""
    for transakcja in transakcje:
        konto = nazwy_kont[transakcja.konto_id]
        kategoria = nazwy_kategorii.get(transakcja.kategoria_id, "-")
        print(f"{transakcja}  [{konto} | {kategoria}]")


def pokaz_konta(salda: list[tuple[Konto, Decimal]], razem: Decimal) -> None:
    """Wypisuje konta z saldami i saldo łączne."""
    for konto, saldo in salda:
        print(f"{str(konto):<40} {formatuj_kwote(saldo):>16}")
    print(f"{'Razem':<40} {formatuj_kwote(razem):>16}")


def pokaz_udzialy(kwoty: dict[str, Decimal], procenty: dict[str, float]) -> None:
    """Wypisuje kategorie z kwotą, procentem i paskiem."""
    for nazwa, kwota in kwoty.items():
        pasek = "█" * max(1, round(procenty[nazwa] / 5))
        procent = formatuj_procent(procenty[nazwa])
        print(f"{nazwa:<25} {formatuj_kwote(kwota):>16} {procent:>7}  {pasek}")


def pokaz_trend(wiersze: list[tuple[date, dict[str, Decimal]]]) -> None:
    """Wypisuje przychody, wydatki i bilans kolejnych miesięcy."""
    kolumny = ("Przychody", "Wydatki", "Bilans")
    print(f"{'Miesiąc':<18}" + "".join(f"{nazwa:>18}" for nazwa in kolumny))
    for miesiac, sumy in wiersze:
        kwoty = "".join(f"{formatuj_kwote(sumy[nazwa]):>18}" for nazwa in kolumny)
        print(f"{formatuj_miesiac(miesiac):<18}{kwoty}")
