"""Kolory i czcionki okna.

Każdy kolor to para: wersja dla motywu jasnego i ciemnego.
"""

from tkinter import Misc, ttk

import customtkinter as ctk

from skarbonka.services.wykresy import CIEMNA, JASNA, Paleta

Kolor = tuple[str, str]

TLO: Kolor = ("#f1f0ec", "#141413")
PASEK_BOCZNY: Kolor = ("#e7e5df", "#1a1a19")
KARTA: Kolor = (JASNA.tlo, CIEMNA.tlo)
OBRAMOWANIE: Kolor = (JASNA.siatka, CIEMNA.siatka)
RAMKA: Kolor = ("#c9c7bf", "#45443f")
TEKST: Kolor = (JASNA.tekst, CIEMNA.tekst)
TEKST_DRUGI: Kolor = (JASNA.tekst_drugi, CIEMNA.tekst_drugi)
AKCENT: Kolor = ("#2165b8", "#2f74c8")
AKCENT_NAJECHANY: Kolor = ("#184e92", "#3d86df")
NAJECHANY: Kolor = ("#dcdad3", "#2a2a28")
WYBRANY: Kolor = (JASNA.tlo, "#55534d")
DOBRY: Kolor = ("#0a7a2f", "#4cc46d")
UWAGA: Kolor = ("#8a5a00", "#e0a526")
ZLY: Kolor = ("#b8322f", "#f07b78")
PRZEZROCZYSTY = "transparent"

RODZINA = "Segoe UI"
STYL_TABELI = "Skarbonka.Treeview"
WYSOKOSC_WIERSZA = 32
DPI_BAZOWE = 96


def czcionka(rozmiar: int = 13, gruba: bool = False) -> ctk.CTkFont:
    """Tworzy czcionkę okna."""
    return ctk.CTkFont(RODZINA, rozmiar, "bold" if gruba else "normal")


def ustaw_motyw(motyw: str) -> None:
    """Włącza motyw jasny albo ciemny."""
    ctk.set_appearance_mode("dark" if motyw == "ciemny" else "light")


def czy_ciemny() -> bool:
    """Informuje, czy działa motyw ciemny."""
    return ctk.get_appearance_mode() == "Dark"


def wybierz(kolor: Kolor) -> str:
    """Zwraca odcień pasujący do motywu."""
    return kolor[1] if czy_ciemny() else kolor[0]


def paleta() -> Paleta:
    """Zwraca paletę wykresów pasującą do motywu."""
    return CIEMNA if czy_ciemny() else JASNA


def ustaw_styl_tabel(okno: Misc) -> None:
    """Dopasowuje tabele do motywu i powiększenia ekranu."""
    skala = okno.winfo_fpixels("1i") / DPI_BAZOWE
    styl = ttk.Style(okno)
    styl.theme_use("clam")
    styl.configure(
        STYL_TABELI,
        background=wybierz(KARTA),
        fieldbackground=wybierz(KARTA),
        foreground=wybierz(TEKST),
        bordercolor=wybierz(KARTA),
        borderwidth=0,
        rowheight=int(WYSOKOSC_WIERSZA * skala),
        font=(RODZINA, 10),
    )
    styl.map(
        STYL_TABELI,
        background=[("selected", wybierz(AKCENT))],
        foreground=[("selected", "#ffffff")],
    )
    styl.configure(
        f"{STYL_TABELI}.Heading",
        background=wybierz(KARTA),
        foreground=wybierz(TEKST_DRUGI),
        relief="flat",
        font=(RODZINA, 9, "bold"),
        padding=(6, 8),
    )
    styl.map(f"{STYL_TABELI}.Heading", background=[("active", wybierz(NAJECHANY))])
    styl.layout(STYL_TABELI, [(f"{STYL_TABELI}.treearea", {"sticky": "nswe"})])
