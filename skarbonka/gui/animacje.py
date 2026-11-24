"""Krótkie animacje elementów okna."""

from collections.abc import Callable
from tkinter import Misc

CZAS = 200
KROK = 12


def animuj(
    element: Misc,
    od: float,
    do: float,
    ustaw: Callable[[float], None],
    po_wszystkim: Callable[[], None] | None = None,
) -> None:
    """Płynnie zmienia wartość, zwalniając pod koniec.

    Gdy element nie jest widoczny, od razu ustawia wartość końcową.
    """
    kroki = CZAS // KROK

    def wykonaj(numer: int) -> None:
        if not element.winfo_exists():
            return
        postep = 1 - (1 - numer / kroki) ** 3
        ustaw(od + (do - od) * postep)
        if numer < kroki:
            element.after(KROK, lambda: wykonaj(numer + 1))
        elif po_wszystkim is not None:
            po_wszystkim()

    wykonaj(1 if element.winfo_toplevel().winfo_viewable() else kroki)
