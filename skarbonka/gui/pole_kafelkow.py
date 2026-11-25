"""Pole formularza z kafelkami, np. kategoriami."""

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from skarbonka.gui import ikony, styl
from skarbonka.gui.pola import SZEROKOSC_POLA
from skarbonka.gui.skladniki import Przewijana, etykieta, pole_tekstowe, przycisk, ramka
from skarbonka.wyjatki import BladSkarbonki

KOLUMNY = 3
PRZERWA = 8
SZEROKOSC_KAFELKA = (SZEROKOSC_POLA - 2 * PRZERWA) // KOLUMNY
SZEROKOSC_PRZYCISKU = 84
NOWY = "Nowa"


class PoleKafelkow(ctk.CTkFrame):
    """Siatka kafelków z ikonami. Ostatni kafelek może dodawać nową pozycję."""

    def __init__(
        self,
        rodzic: Any,
        wartosci: list[str],
        po_zmianie: Callable[[], None],
        dodaj: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__(rodzic, fg_color=styl.PRZEZROCZYSTY)
        self._po_zmianie = po_zmianie
        self._dodaj = dodaj
        self._kafelki: dict[str, ctk.CTkFrame] = {}
        self._wybrany = wartosci[0]
        self._siatka = ramka(self)
        self._siatka.pack(anchor="w")
        for nazwa in wartosci:
            self._kafelki[nazwa] = self._utworz(
                nazwa, ikony.dla_nazwy(nazwa), lambda n=nazwa: self._kliknij(n)
            )
        self._nowy = None
        if dodaj is not None:
            self._nowy = self._utworz(NOWY, ikony.PLUS, self.otworz_nowa)
            self._pomaluj(self._nowy, styl.PRZEZROCZYSTY, styl.RAMKA, styl.TEKST_DRUGI)
            self._buduj_dodawanie()
        self._uloz()
        self.set(self._wybrany)

    def _utworz(self, nazwa: str, znak: str, akcja: Callable[[], None]) -> ctk.CTkFrame:
        """Tworzy jeden kafelek."""
        kafelek = ctk.CTkFrame(
            self._siatka,
            width=SZEROKOSC_KAFELKA,
            height=72,
            corner_radius=11,
            border_width=2,
            cursor="hand2",
        )
        kafelek.pack_propagate(False)
        srodek = ramka(kafelek)
        srodek.pack(expand=True)
        ikona = ctk.CTkLabel(srodek, text=znak, font=styl.czcionka(19, "ikony"), height=24)
        napis = ctk.CTkLabel(
            srodek,
            text=nazwa,
            font=styl.czcionka(11),
            height=16,
            wraplength=SZEROKOSC_KAFELKA - 12,
        )
        ikona.pack()
        napis.pack(pady=(3, 0))
        kafelek.napisy = (ikona, napis)
        for element in (kafelek, srodek, ikona, napis):
            element.bind("<Button-1>", lambda _: akcja())
        return kafelek

    def _uloz(self) -> None:
        """Układa kafelki w rzędach. Kafelek dodawania jest ostatni."""
        wszystkie = [*self._kafelki.values(), *([self._nowy] if self._nowy else [])]
        for numer, kafelek in enumerate(wszystkie):
            rzad, kolumna = divmod(numer, KOLUMNY)
            odstep = (0 if kolumna == 0 else PRZERWA, 0)
            kafelek.grid(row=rzad, column=kolumna, padx=odstep, pady=(0, PRZERWA))

    def _buduj_dodawanie(self) -> None:
        """Tworzy ukryty rząd z nazwą nowej pozycji."""
        self._dodawanie = ramka(self)
        rzad = ramka(self._dodawanie)
        rzad.pack(anchor="w")
        szerokosc = SZEROKOSC_POLA - SZEROKOSC_PRZYCISKU - PRZERWA
        self.nazwa = pole_tekstowe(rzad, szerokosc, "Nazwa nowej kategorii")
        self.nazwa.pack(side="left")
        self.nazwa.bind("<Return>", lambda _: self._enter())
        przycisk(rzad, "Dodaj", self.dodaj_nowa, "glowny", SZEROKOSC_PRZYCISKU).pack(
            side="left", padx=(PRZERWA, 0)
        )
        self.blad = etykieta(self._dodawanie, "", 12, kolor=styl.ZLY)
        self.blad.configure(wraplength=SZEROKOSC_POLA)

    def otworz_nowa(self) -> None:
        """Pokazuje albo chowa rząd dodawania."""
        if self._dodawanie.winfo_manager():
            self._dodawanie.pack_forget()
            return
        self._dodawanie.pack(anchor="w", pady=(0, PRZERWA))
        self.nazwa.focus_set()
        self._przewin()

    def _przewin(self) -> None:
        """Przewija panel do rzędu dodawania."""
        if isinstance(self.master, Przewijana):
            self.master.pokaz(self._dodawanie)

    def _enter(self) -> str:
        """Dodaje pozycję. Zwrócone słowo zatrzymuje Enter, żeby nie zapisał całego panelu."""
        self.dodaj_nowa()
        return "break"

    def dodaj_nowa(self) -> None:
        """Dodaje i wybiera nową pozycję. Przy błędnej nazwie pokazuje powód."""
        try:
            nazwa = self._dodaj(self.nazwa.get())
        except BladSkarbonki as blad:
            self.blad.configure(text=str(blad))
            self.blad.pack(anchor="w", pady=(4, 0))
            self._przewin()
            return
        self.blad.pack_forget()
        self.nazwa.delete(0, "end")
        self._dodawanie.pack_forget()
        self._kafelki[nazwa] = self._utworz(
            nazwa, ikony.dla_nazwy(nazwa), lambda: self._kliknij(nazwa)
        )
        self._uloz()
        self._kliknij(nazwa)

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
            if nazwa == tekst:
                self._pomaluj(kafelek, styl.AKCENT_TLO, styl.AKCENT_TEKST, styl.AKCENT_TEKST)
            else:
                self._pomaluj(kafelek, styl.WGLEBIENIE, styl.WGLEBIENIE, styl.TEKST_DRUGI)

    @staticmethod
    def _pomaluj(
        kafelek: ctk.CTkFrame, tlo: styl.Kolor, obwodka: styl.Kolor, tekst: styl.Kolor
    ) -> None:
        """Ustawia kolory kafelka."""
        kafelek.configure(fg_color=tlo, border_color=obwodka)
        for napis in kafelek.napisy:
            napis.configure(text_color=tekst, fg_color=tlo)
