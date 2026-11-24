"""Komunikaty pokazywane, gdy główne okno jeszcze nie działa albo już nie działa."""

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox
from typing import Any

from skarbonka.config import NAZWA_APLIKACJI


def pokaz(tekst: str) -> None:
    """Pokazuje komunikat z przyciskiem OK."""
    _z_ukrytym_oknem(messagebox.showinfo, tekst)


def zapytaj(tekst: str) -> bool:
    """Zadaje pytanie tak/nie."""
    return _z_ukrytym_oknem(messagebox.askyesno, tekst)


def _z_ukrytym_oknem(funkcja: Callable[..., Any], tekst: str) -> Any:
    """Tworzy niewidoczne okno potrzebne do pokazania komunikatu."""
    okno = tk.Tk()
    okno.withdraw()
    try:
        return funkcja(NAZWA_APLIKACJI, tekst, parent=okno)
    finally:
        okno.destroy()
