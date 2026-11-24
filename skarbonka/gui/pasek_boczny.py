"""Pasek boczny: logo, nawigacja i zmiana motywu."""

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from skarbonka import __version__
from skarbonka.config import NAZWA_APLIKACJI
from skarbonka.gui import ikony, styl
from skarbonka.gui.skladniki import etykieta, kafelek_ikony, ramka

SZEROKOSC = 228


class PozycjaMenu(ctk.CTkFrame):
    """Pozycja nawigacji z ikoną, znacznikiem i licznikiem."""

    def __init__(self, rodzic: Any, ikona: str, tekst: str, akcja: Callable[[], Any]) -> None:
        super().__init__(rodzic, height=44, corner_radius=11, fg_color=styl.MARKA, cursor="hand2")
        self.pack_propagate(False)
        self._wybrana = False
        self._znacznik = ctk.CTkFrame(
            self, width=3, height=18, corner_radius=2, fg_color=styl.PRZEZROCZYSTY
        )
        self._znacznik.pack(side="left", padx=(8, 0))
        self._ikona = ctk.CTkLabel(
            self, text=ikona, width=34, font=styl.czcionka(16, "ikony")
        )
        self._ikona.pack(side="left", padx=(4, 4))
        self._napis = etykieta(self, tekst, 14, "mocny")
        self._napis.pack(side="left")
        self._licznik = ctk.CTkLabel(
            self,
            text="",
            width=22,
            height=20,
            corner_radius=7,
            font=styl.czcionka(11, "mocny"),
            fg_color=styl.MOSIADZ,
            text_color="#2b1d00",
        )
        for element in (self, self._ikona, self._napis):
            element.bind("<Button-1>", lambda _: akcja())
            element.bind("<Enter>", lambda _: self._pomaluj(najechana=True))
            element.bind("<Leave>", lambda _: self._pomaluj())
        self._pomaluj()

    def ustaw(self, wybrana: bool) -> None:
        """Oznacza pozycję jako wybraną."""
        self._wybrana = wybrana
        self._pomaluj()

    def ustaw_licznik(self, liczba: int) -> None:
        """Pokazuje liczbę spraw do załatwienia."""
        if liczba:
            self._licznik.configure(text=str(liczba))
            self._licznik.pack(side="right", padx=12)
        else:
            self._licznik.pack_forget()

    def _pomaluj(self, najechana: bool = False) -> None:
        """Dobiera kolory do stanu."""
        if self._wybrana:
            tlo = styl.MARKA_WYBRANA
        else:
            tlo = styl.MARKA_NAJECHANA if najechana else styl.MARKA
        kolor = styl.BIALY if self._wybrana or najechana else styl.MARKA_TEKST
        self.configure(fg_color=tlo)
        self._znacznik.configure(fg_color=styl.MOSIADZ if self._wybrana else tlo)
        self._ikona.configure(text_color=kolor, fg_color=tlo)
        self._napis.configure(text_color=kolor, fg_color=tlo)


class PasekBoczny(ctk.CTkFrame):
    """Zielony pasek z nawigacją."""

    def __init__(
        self,
        rodzic: Any,
        pozycje: list[tuple[str, str]],
        po_wyborze: Callable[[str], Any],
        po_motywie: Callable[[], Any],
    ) -> None:
        super().__init__(rodzic, width=SZEROKOSC, fg_color=styl.MARKA, corner_radius=0)
        self.pack_propagate(False)
        logo = ramka(self)
        logo.pack(fill="x", padx=18, pady=(26, 30))
        kafelek_ikony(logo, ikony.KARTA, styl.MOSIADZ, styl.MARKA, bok=42).pack(side="left")
        etykieta(logo, NAZWA_APLIKACJI, 20, "naglowek", styl.BIALY).pack(side="left", padx=12)

        self._pozycje: dict[str, PozycjaMenu] = {}
        for ikona, tytul in pozycje:
            pozycja = PozycjaMenu(self, ikona, tytul, lambda t=tytul: po_wyborze(t))
            pozycja.pack(fill="x", padx=12, pady=2)
            self._pozycje[tytul] = pozycja

        etykieta(self, f"wersja {__version__}", 11, kolor=styl.MARKA_TEKST).pack(
            side="bottom", anchor="w", padx=24, pady=(6, 20)
        )
        self._motyw = PozycjaMenu(self, ikony.KSIEZYC, "Zmień motyw", po_motywie)
        self._motyw.pack(side="bottom", fill="x", padx=12)

    def wybierz(self, tytul: str) -> None:
        """Oznacza wybraną pozycję."""
        for nazwa, pozycja in self._pozycje.items():
            pozycja.ustaw(nazwa == tytul)

    def ustaw_licznik(self, tytul: str, liczba: int) -> None:
        """Pokazuje licznik przy pozycji."""
        self._pozycje[tytul].ustaw_licznik(liczba)
