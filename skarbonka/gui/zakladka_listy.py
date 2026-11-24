"""Klasa bazowa zakładek z listą, dodawaniem i usuwaniem."""

from abc import abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from skarbonka.config import MAKS_DLUGOSC_NAZWY
from skarbonka.gui import ikony, styl
from skarbonka.gui.formularz import Formularz
from skarbonka.gui.lista import Lista, Pozycja
from skarbonka.gui.skladniki import Karta, etykieta, przycisk, ramka
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
    """Lista z przyciskami Dodaj i Usuń."""

    OPIS = ""
    PUSTO = (ikony.ARCHIWUM, "Nic tu jeszcze nie ma.")

    def __init__(self, rodzic: Any, okno: "Okno") -> None:
        super().__init__(rodzic, fg_color=styl.PRZEZROCZYSTY)
        self.okno = okno
        self.serwisy = okno.serwisy
        self.gora = ramka(self)
        self.gora.pack(fill="x", pady=(0, 16))
        etykieta(self.gora, self.OPIS, kolor=styl.TEKST_DRUGI).pack(side="left")
        przycisk(self.gora, "Dodaj", self.dodaj, "glowny", 90).pack(side="right")
        karta = Karta(self)
        karta.pack(fill="both", expand=True)
        self._akcje = ctk.CTkFrame(karta, fg_color=styl.AKCENT_TLO, corner_radius=12)
        self._nazwa_wybranej = etykieta(self._akcje, "", 13, "mocny", styl.AKCENT_TEKST)
        self._nazwa_wybranej.pack(side="left", padx=18)
        przycisk(self._akcje, "Usuń", self.usun, "grozny", 80, 34).pack(
            side="right", padx=8, pady=8
        )
        self.dodaj_akcje(self._akcje)
        self.tabela = Lista(karta, self._wybrano, pusto=self.PUSTO)
        self.tabela.pack(fill="both", expand=True, padx=10, pady=12)

    def dodaj_akcje(self, rzad: ctk.CTkFrame) -> None:
        """Miejsce na dodatkowe przyciski zaznaczonej pozycji."""

    @abstractmethod
    def pozycje(self) -> list[Pozycja]:
        """Zwraca pozycje listy."""

    @abstractmethod
    def dodaj(self) -> Formularz | None:
        """Otwiera panel nowej pozycji."""

    @abstractmethod
    def usun_rekord(self, numer: int) -> None:
        """Usuwa pozycję o podanym numerze."""

    def odswiez(self) -> None:
        """Wczytuje aktualne dane."""
        self.tabela.wypelnij(self.pozycje())
        self._wybrano()

    def wybrany_numer(self) -> int:
        """Zwraca numer zaznaczonej pozycji."""
        numer = self.tabela.zaznaczony()
        if numer is None:
            raise NieZnalezionoRekordu("Najpierw zaznacz pozycję na liście.")
        return numer

    def usun(self) -> None:
        """Usuwa zaznaczoną pozycję po potwierdzeniu."""
        numer = self.wybrany_numer()
        nazwa = self.tabela.pozycja(numer).tytul
        if self.okno.zapytaj(f"Usunąć „{nazwa}”?", "Usuń", grozne=True):
            self.usun_rekord(numer)
            self.okno.powiadom("Usunięto.")
            self.okno.odswiez()

    def _wybrano(self) -> None:
        """Pokazuje przyciski dla zaznaczonej pozycji."""
        numer = self.tabela.zaznaczony()
        if numer is None:
            self._akcje.pack_forget()
            return
        self._nazwa_wybranej.configure(text=self.tabela.pozycja(numer).tytul)
        self._akcje.pack(side="bottom", fill="x", padx=12, pady=(0, 12))
