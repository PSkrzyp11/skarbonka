"""Pola formularza. Każde ma metody get() i set()."""

from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import customtkinter as ctk

from skarbonka.gui import styl
from skarbonka.gui.skladniki import lista_rozwijana, pole_tekstowe, przycisk
from skarbonka.models.enums import Czestotliwosc
from skarbonka.utils.formatowanie import formatuj_date

SZEROKOSC_POLA = 340
SZEROKOSC_LICZBY = 76
ODSTEP = 10


class PoleTekstowe(ctk.CTkFrame):
    """Zwykłe pole tekstowe."""

    def __init__(self, rodzic: Any, po_zmianie: Callable[[], None]) -> None:
        super().__init__(rodzic, fg_color=styl.PRZEZROCZYSTY)
        self.wpis = pole_tekstowe(self, SZEROKOSC_POLA)
        self.wpis.pack(side="left")
        self.wpis.bind("<KeyRelease>", lambda _: po_zmianie())

    def get(self) -> str:
        """Zwraca wpisany tekst."""
        return self.wpis.get()

    def set(self, tekst: str) -> None:
        """Zmienia tekst."""
        if tekst or self.get():
            self.wpis.delete(0, "end")
            self.wpis.insert(0, tekst)

    def ustaw_kursor(self) -> None:
        """Ustawia kursor w polu."""
        self.wpis.focus_set()
        self.wpis.select_range(0, "end")

    def oznacz_blad(self, czy_blad: bool) -> None:
        """Podświetla ramkę pola."""
        self.wpis.configure(border_color=styl.ZLY if czy_blad else styl.RAMKA)


class PoleKwoty(PoleTekstowe):
    """Duże pole kwoty z jednostką."""

    def __init__(self, rodzic: Any, po_zmianie: Callable[[], None], jednostka: str = "zł") -> None:
        super().__init__(rodzic, po_zmianie)
        self.wpis.configure(
            width=SZEROKOSC_POLA - 50,
            height=58,
            font=styl.czcionka(30, "liczby"),
            border_width=0,
            fg_color=styl.KARTA,
            placeholder_text="0,00",
        )
        self.jednostka = ctk.CTkLabel(
            self, text=jednostka, font=styl.czcionka(22, "liczby"), text_color=styl.TEKST_DRUGI
        )
        self.jednostka.pack(side="left", padx=6)

    def oznacz_blad(self, czy_blad: bool) -> None:
        """Zmienia kolor kwoty."""
        self.wpis.configure(text_color=styl.ZLY if czy_blad else styl.TEKST)


class PoleDaty(PoleTekstowe):
    """Pole daty ze skrótami."""

    def __init__(self, rodzic: Any, po_zmianie: Callable[[], None]) -> None:
        super().__init__(rodzic, po_zmianie)
        self.wpis.configure(width=SZEROKOSC_POLA - 170)
        for napis, dni in (("Dziś", 0), ("Wczoraj", 1)):
            dzien = date.today() - timedelta(days=dni)
            przycisk(self, napis, lambda d=dzien: self.set(formatuj_date(d)), "cichy", 70).pack(
                side="left", padx=(8, 0)
            )


class PoleOdstepu(PoleTekstowe):
    """Liczba i jednostka, np. 2 miesiące."""

    def __init__(self, rodzic: Any, po_zmianie: Callable[[], None]) -> None:
        def zmieniono() -> None:
            self._odmien()
            po_zmianie()

        super().__init__(rodzic, zmieniono)
        self._jednostka = Czestotliwosc.MIESIAC
        self.wpis.configure(width=SZEROKOSC_LICZBY, justify="center")
        self.menu = lista_rozwijana(
            self, [], self._wybrano, SZEROKOSC_POLA - SZEROKOSC_LICZBY - ODSTEP
        )
        self.menu.pack(side="left", padx=(ODSTEP, 0))
        self._odmien()

    def get(self) -> str:
        """Zwraca liczbę i jednostkę."""
        return f"{self.wpis.get()} {self.menu.get()}"

    def set(self, tekst: str) -> None:
        """Ustawia liczbę i jednostkę."""
        liczba, _, jednostka = tekst.rpartition(" ")
        self.wpis.delete(0, "end")
        self.wpis.insert(0, liczba)
        self._wybrano(jednostka)

    def _wybrano(self, nazwa: str) -> None:
        self._jednostka = Czestotliwosc.z_odmiany(nazwa)
        self._odmien()

    def _odmien(self) -> None:
        """Dopasowuje nazwy jednostek do wpisanej liczby."""
        liczba = self.wpis.get().strip()
        ile = int(liczba) if liczba.isdecimal() else 1
        self.menu.configure(values=[jednostka.odmiana(ile) for jednostka in Czestotliwosc])
        self.menu.set(self._jednostka.odmiana(ile))


class PoleListy(ctk.CTkFrame):
    """Rozwijana lista."""

    def __init__(self, rodzic: Any, wartosci: list[str], po_zmianie: Callable[[], None]) -> None:
        super().__init__(rodzic, fg_color=styl.PRZEZROCZYSTY)
        self.menu = lista_rozwijana(self, wartosci, lambda _: po_zmianie(), SZEROKOSC_POLA)
        self.menu.pack(side="left")
        self.menu.set(wartosci[0])

    def get(self) -> str:
        """Zwraca wybraną wartość."""
        return self.menu.get()

    def set(self, tekst: str) -> None:
        """Wybiera wartość."""
        self.menu.set(tekst)
