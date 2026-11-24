"""Klasa bazowa zakładek z listą, dodawaniem i usuwaniem."""

from abc import abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

import customtkinter as ctk

from skarbonka.config import MAKS_DLUGOSC_NAZWY
from skarbonka.gui import styl
from skarbonka.gui.formularz import Formularz
from skarbonka.gui.skladniki import Karta, Kolumna, Tabela, Wiersz, przycisk
from skarbonka.utils.walidacja import sprawdz_tekst
from skarbonka.wyjatki import NieZnalezionoRekordu

if TYPE_CHECKING:
    from skarbonka.gui.okno import Okno


def parser_nazwy(sprawdz: Callable[[str], None]) -> Callable[[str], str]:
    """Zwraca funkcję, która sprawdza nazwę i to, czy jest wolna."""

    def parser(tekst: str) -> str:
        nazwa = sprawdz_tekst(tekst, "Nazwa", MAKS_DLUGOSC_NAZWY)
        sprawdz(nazwa)
        return nazwa

    return parser


class ZakladkaListy(ctk.CTkFrame):
    """Tabela z przyciskami Dodaj i Usuń."""

    KOLUMNY: ClassVar[list[Kolumna]] = []

    def __init__(self, rodzic: Any, okno: "Okno") -> None:
        super().__init__(rodzic, fg_color=styl.PRZEZROCZYSTY)
        self.okno = okno
        self.serwisy = okno.serwisy
        gora = ctk.CTkFrame(self, fg_color=styl.PRZEZROCZYSTY)
        gora.pack(fill="x", pady=(6, 10))
        przycisk(gora, "Dodaj", self.dodaj, glowny=True).pack(side="right")
        przycisk(gora, "Usuń", self.usun).pack(side="right", padx=8)
        karta = Karta(self)
        karta.pack(fill="both", expand=True)
        self.tabela = Tabela(karta, self.KOLUMNY)
        self.tabela.pack(fill="both", expand=True, padx=10, pady=10)

    @abstractmethod
    def wiersze(self) -> list[Wiersz]:
        """Zwraca wiersze tabeli."""

    @abstractmethod
    def dodaj(self) -> Formularz | None:
        """Otwiera formularz nowej pozycji."""

    @abstractmethod
    def usun_rekord(self, numer: int) -> None:
        """Usuwa pozycję o podanym numerze."""

    def odswiez(self) -> None:
        """Wczytuje aktualne dane."""
        self.tabela.wypelnij(self.wiersze())

    def usun(self) -> None:
        """Usuwa zaznaczoną pozycję po potwierdzeniu."""
        numer = self.tabela.zaznaczony()
        if numer is None:
            raise NieZnalezionoRekordu("Najpierw zaznacz pozycję na liście.")
        nazwa = self.tabela.komorka(numer, 0)
        if self.okno.zapytaj(f"Usunąć „{nazwa}”?"):
            self.usun_rekord(numer)
            self.okno.powiadom("Usunięto.")
            self.odswiez()
