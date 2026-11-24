"""Obliczenia na datach."""

import calendar
from datetime import date


def przesun_miesiac(dzien: date, ile: int) -> date:
    """Przesuwa datę o podaną liczbę miesięcy.

    Gdy w docelowym miesiącu nie ma takiego dnia, wybiera ostatni możliwy,
    np. 31 stycznia + 1 miesiąc to 28 lub 29 lutego.
    """
    numer = dzien.year * 12 + dzien.month - 1 + ile
    rok, miesiac = numer // 12, numer % 12 + 1
    return date(rok, miesiac, min(dzien.day, dni_miesiaca(rok, miesiac)))


def dni_miesiaca(rok: int, miesiac: int) -> int:
    """Zwraca liczbę dni miesiąca."""
    return calendar.monthrange(rok, miesiac)[1]
