"""Kolory, czcionki i pasek tytułu okna.

Każdy kolor to para: wersja dla motywu jasnego i ciemnego. Wszystkie szarości
mają ten sam ciepły odcień, a zieleń jest jedynym kolorem akcentu.
"""

import sys
from functools import lru_cache
from tkinter import Misc, font

import customtkinter as ctk

from skarbonka.services.wykresy import CIEMNA, JASNA, Paleta

Kolor = tuple[str, str]

TLO: Kolor = ("#f3f1ea", "#121513")
KARTA: Kolor = (JASNA.tlo, CIEMNA.tlo)
WGLEBIENIE: Kolor = ("#ece9df", "#242a26")
NAJECHANY: Kolor = ("#f1eee5", "#212723")
WYBRANY: Kolor = (JASNA.tlo, "#3a443d")
LINIA: Kolor = (JASNA.siatka, CIEMNA.siatka)
RAMKA: Kolor = ("#cdc8b9", "#3d4640")

TEKST: Kolor = (JASNA.tekst, CIEMNA.tekst)
TEKST_DRUGI: Kolor = (JASNA.tekst_drugi, CIEMNA.tekst_drugi)
BIALY: Kolor = ("#ffffff", "#ffffff")

MARKA: Kolor = ("#12392f", "#0d2a22")
MARKA_NAJECHANA: Kolor = ("#1b4a3e", "#143a30")
MARKA_WYBRANA: Kolor = ("#245c4d", "#1c4b3e")
MARKA_TEKST: Kolor = ("#b9d0c7", "#9fbab0")
MOSIADZ: Kolor = ("#e0b04f", "#d9a441")

AKCENT: Kolor = ("#14684f", "#1f7c60")
AKCENT_NAJECHANY: Kolor = ("#0f5440", "#259070")
AKCENT_TEKST: Kolor = ("#14684f", "#62c6a1")
AKCENT_TLO: Kolor = ("#dcebe3", "#1c382f")

DOBRY: Kolor = ("#14684f", "#62c6a1")
UWAGA: Kolor = ("#8f5d08", "#e3b254")
UWAGA_TLO: Kolor = ("#f6e8c9", "#3a2f17")
ZLY: Kolor = ("#a9362c", "#ef877c")
ZLY_TLO: Kolor = ("#f6dfda", "#3d2320")
PRZEZROCZYSTY = "transparent"

KROJE = {
    "tresc": ("Segoe UI Variable Text", "Segoe UI"),
    "mocny": ("Segoe UI Semibold", "Segoe UI"),
    "naglowek": ("Segoe UI Variable Display", "Segoe UI"),
    "liczby": ("Bahnschrift", "Segoe UI"),
    "ikony": ("Segoe Fluent Icons", "Segoe MDL2 Assets"),
}

DPI_BAZOWE = 96
DWM_KOLOR_PASKA = 35
DWM_KOLOR_TEKSTU = 36


@lru_cache
def rodzina(kroj: str) -> str:
    """Zwraca pierwszą czcionkę kroju, która jest w systemie."""
    dostepne = set(font.families())
    return next((nazwa for nazwa in KROJE[kroj] if nazwa in dostepne), KROJE[kroj][-1])


def czcionka(rozmiar: int = 13, kroj: str = "tresc") -> ctk.CTkFont:
    """Tworzy czcionkę okna."""
    return ctk.CTkFont(rodzina(kroj), rozmiar, "bold" if kroj == "naglowek" else "normal")


def skala(element: Misc) -> float:
    """Zwraca powiększenie ekranu: 1 to 100 procent."""
    return element.winfo_fpixels("1i") / DPI_BAZOWE


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


def paleta_marki() -> Paleta:
    """Zwraca paletę wykresu leżącego na zielonym tle."""
    tlo = wybierz(MARKA)
    return Paleta(tlo, "#ffffff", wybierz(MARKA_TEKST), tlo, wybierz(MOSIADZ), "#ffffff")


def pomaluj_pasek_tytulu(okno: Misc) -> None:
    """Dopasowuje pasek tytułu do tła. Starsze wersje Windows ignorują polecenie."""
    if sys.platform != "win32":
        return
    import ctypes

    uchwyt = ctypes.windll.user32.GetParent(okno.winfo_id())
    for atrybut, kolor in ((DWM_KOLOR_PASKA, TLO), (DWM_KOLOR_TEKSTU, TEKST)):
        czerwony, zielony, niebieski = bytes.fromhex(wybierz(kolor)[1:])
        wartosc = ctypes.c_int(czerwony | zielony << 8 | niebieski << 16)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            uchwyt, atrybut, ctypes.byref(wartosc), ctypes.sizeof(wartosc)
        )
