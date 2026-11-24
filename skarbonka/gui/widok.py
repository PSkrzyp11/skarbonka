"""Klasa bazowa widoków, czyli stron okna."""

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from skarbonka.gui import ikony, styl
from skarbonka.gui.skladniki import etykieta, ramka

if TYPE_CHECKING:
    from skarbonka.gui.okno import Okno


class Widok(ctk.CTkFrame):
    """Strona okna: tytuł z podtytułem, pasek przycisków i treść."""

    TYTUL = ""
    IKONA = ikony.DOM

    def __init__(self, rodzic: Any, okno: "Okno") -> None:
        super().__init__(rodzic, fg_color=styl.PRZEZROCZYSTY)
        self.okno = okno
        self.serwisy = okno.serwisy
        gora = ramka(self)
        gora.pack(fill="x", padx=36, pady=(30, 20))
        napisy = ramka(gora)
        napisy.pack(side="left")
        etykieta(napisy, self.TYTUL, 30, "naglowek").pack(anchor="w")
        self.podtytul = etykieta(napisy, "", 13, kolor=styl.TEKST_DRUGI)
        self.podtytul.pack(anchor="w", pady=(2, 0))
        self.pasek = ramka(gora)
        self.pasek.pack(side="right", anchor="s")
        self.tresc = ramka(self)
        self.tresc.pack(fill="both", expand=True, padx=36, pady=(0, 30))
        self.buduj()

    @abstractmethod
    def buduj(self) -> None:
        """Tworzy elementy widoku. Wywoływana raz."""

    @abstractmethod
    def odswiez(self) -> None:
        """Wczytuje aktualne dane do elementów widoku."""
