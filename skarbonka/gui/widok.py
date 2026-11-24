"""Klasa bazowa widoków, czyli stron okna."""

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from skarbonka.gui import styl
from skarbonka.gui.skladniki import etykieta

if TYPE_CHECKING:
    from skarbonka.gui.okno import Okno


class Widok(ctk.CTkFrame):
    """Strona okna: tytuł, pasek przycisków i treść."""

    TYTUL = ""

    def __init__(self, rodzic: Any, okno: "Okno") -> None:
        super().__init__(rodzic, fg_color=styl.PRZEZROCZYSTY)
        self.okno = okno
        self.serwisy = okno.serwisy
        gora = ctk.CTkFrame(self, fg_color=styl.PRZEZROCZYSTY)
        gora.pack(fill="x", padx=28, pady=(22, 14))
        etykieta(gora, self.TYTUL, 24, gruba=True).pack(side="left")
        self.pasek = ctk.CTkFrame(gora, fg_color=styl.PRZEZROCZYSTY, width=0, height=0)
        self.pasek.pack(side="right")
        self.tresc = ctk.CTkFrame(self, fg_color=styl.PRZEZROCZYSTY)
        self.tresc.pack(fill="both", expand=True, padx=28, pady=(0, 8))
        self.buduj()

    @abstractmethod
    def buduj(self) -> None:
        """Tworzy elementy widoku. Wywoływana raz."""

    @abstractmethod
    def odswiez(self) -> None:
        """Wczytuje aktualne dane do elementów widoku."""
