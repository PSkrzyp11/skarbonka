"""Pola formularza. Każde ma metody get() i set()."""

from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import customtkinter as ctk

from skarbonka.gui import ikony, styl
from skarbonka.gui.skladniki import lista_rozwijana, pole_tekstowe, przycisk, ramka
from skarbonka.utils.formatowanie import formatuj_date

SZEROKOSC_POLA = 340
KOLUMNY_KAFELKOW = 3


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


class PoleKafelkow(ctk.CTkFrame):
    """Siatka kafelków z ikonami, np. kategorie."""

    def __init__(self, rodzic: Any, wartosci: list[str], po_zmianie: Callable[[], None]) -> None:
        super().__init__(rodzic, fg_color=styl.PRZEZROCZYSTY)
        self._po_zmianie = po_zmianie
        self._kafelki: dict[str, ctk.CTkFrame] = {}
        self._wybrany = wartosci[0]
        szerokosc = (SZEROKOSC_POLA - 16) // KOLUMNY_KAFELKOW
        for numer, nazwa in enumerate(wartosci):
            kafelek = self._utworz(nazwa, szerokosc)
            kafelek.grid(
                row=numer // KOLUMNY_KAFELKOW,
                column=numer % KOLUMNY_KAFELKOW,
                padx=(0 if numer % KOLUMNY_KAFELKOW == 0 else 8, 0),
                pady=(0, 8),
            )
            self._kafelki[nazwa] = kafelek
        self.set(self._wybrany)

    def _utworz(self, nazwa: str, szerokosc: int) -> ctk.CTkFrame:
        """Tworzy jeden kafelek."""
        kafelek = ctk.CTkFrame(
            self, width=szerokosc, height=72, corner_radius=11, border_width=2, cursor="hand2"
        )
        kafelek.pack_propagate(False)
        srodek = ramka(kafelek)
        srodek.pack(expand=True)
        ikona = ctk.CTkLabel(
            srodek, text=ikony.dla_nazwy(nazwa), font=styl.czcionka(19, "ikony"), height=24
        )
        napis = ctk.CTkLabel(
            srodek, text=nazwa, font=styl.czcionka(11), height=16, wraplength=szerokosc - 12
        )
        ikona.pack()
        napis.pack(pady=(3, 0))
        kafelek.napisy = (ikona, napis)
        for element in (kafelek, srodek, ikona, napis):
            element.bind("<Button-1>", lambda _: self._kliknij(nazwa))
        return kafelek

    def _kliknij(self, nazwa: str) -> None:
        self.set(nazwa)
        self._po_zmianie()

    def get(self) -> str:
        """Zwraca wybraną nazwę."""
        return self._wybrany

    def set(self, tekst: str) -> None:
        """Wybiera kafelek."""
        self._wybrany = tekst
        for nazwa, kafelek in self._kafelki.items():
            wybrany = nazwa == tekst
            tlo = styl.AKCENT_TLO if wybrany else styl.WGLEBIENIE
            kafelek.configure(fg_color=tlo, border_color=styl.AKCENT_TEKST if wybrany else tlo)
            for napis in kafelek.napisy:
                napis.configure(
                    text_color=styl.AKCENT_TEKST if wybrany else styl.TEKST_DRUGI, fg_color=tlo
                )
