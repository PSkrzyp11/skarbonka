"""Analizy: wykresy i prognoza."""

from datetime import date
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from skarbonka.gui import styl
from skarbonka.gui.skladniki import Kafelek, Karta, WyborMiesiaca, Wykres, etykieta, przycisk
from skarbonka.gui.widok import Widok
from skarbonka.services import analizy, wykresy
from skarbonka.utils.formatowanie import formatuj_date, formatuj_kwote
from skarbonka.wyjatki import BladPliku, ZaMaloDanych

KATEGORIE, TREND, SALDO = "Kategorie", "Trend", "Saldo"


class WidokAnalizy(Widok):
    """Wykresy z wybranego miesiąca i prognoza."""

    TYTUL = "Analizy"

    def buduj(self) -> None:
        self.rodzaj = ctk.CTkSegmentedButton(
            self.pasek,
            values=[KATEGORIE, TREND, SALDO],
            font=styl.czcionka(),
            height=34,
            fg_color=styl.NAJECHANY,
            selected_color=styl.WYBRANY,
            selected_hover_color=styl.WYBRANY,
            unselected_color=styl.NAJECHANY,
            unselected_hover_color=styl.OBRAMOWANIE,
            text_color=styl.TEKST,
            command=lambda _: self.odswiez(),
        )
        self.rodzaj.set(KATEGORIE)
        self.rodzaj.pack(side="left", padx=(0, 10))
        przycisk(self.pasek, "Zapisz PNG", self.zapisz_png).pack(side="left")

        prognoza = Karta(self.tresc, "Prognoza salda na koniec miesiąca")
        prognoza.pack(side="bottom", fill="x", pady=(14, 0))
        self._opis_prognozy = etykieta(prognoza, "", 12, kolor=styl.TEKST_DRUGI)
        self._opis_prognozy.pack(anchor="w", padx=16)
        rzad = ctk.CTkFrame(prognoza, fg_color=styl.PRZEZROCZYSTY)
        rzad.pack(fill="x", padx=16, pady=12)
        nazwy = ("Optymistycznie", "Realistycznie", "Pesymistycznie")
        self.kafelki = [Kafelek(rzad, nazwa) for nazwa in nazwy]
        for i, kafelek in enumerate(self.kafelki):
            rzad.grid_columnconfigure(i, weight=1, uniform="prognoza")
            kafelek.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))

        karta = Karta(self.tresc)
        karta.pack(fill="both", expand=True)
        self.miesiac = WyborMiesiaca(karta, self.odswiez)
        self.wykres = Wykres(karta)
        self.wykres.pack(side="bottom", fill="both", expand=True, padx=10, pady=10)

    def odswiez(self) -> None:
        rodzaj = self.rodzaj.get()
        if rodzaj == KATEGORIE:
            self.miesiac.pack(side="top", pady=(12, 0))
        else:
            self.miesiac.pack_forget()
        rysuj = {KATEGORIE: self._kategorie, TREND: self._trend, SALDO: self._saldo}
        rysuj[rodzaj]()
        self._pokaz_prognoze()

    def _kategorie(self) -> None:
        """Pokazuje wydatki wybranego miesiąca."""
        wybrane = analizy.z_miesiaca(self.serwisy.transakcje.wszystkie(), self.miesiac.miesiac)
        kwoty = analizy.wydatki_wg_kategorii(wybrane, self.serwisy.kategorie.wszystkie())
        if kwoty:
            self.wykres.pokaz(wykresy.rysuj_kategorie(kwoty, paleta=styl.paleta()))
        else:
            self.wykres.pusty("Brak wydatków w tym miesiącu.")

    def _trend(self) -> None:
        """Pokazuje przychody i wydatki z 6 miesięcy."""
        wiersze = analizy.trend(self.serwisy.transakcje.wszystkie())
        self.wykres.pokaz(wykresy.rysuj_trend(wiersze, paleta=styl.paleta()))

    def _saldo(self) -> None:
        """Pokazuje saldo z 90 dni."""
        historia = analizy.historia_salda(
            self.serwisy.transakcje.wszystkie(), self.serwisy.konta.saldo(), date.today()
        )
        self.wykres.pokaz(wykresy.rysuj_saldo(historia, paleta=styl.paleta()))

    def _pokaz_prognoze(self) -> None:
        """Wypisuje prognozę albo powód, dla którego jej nie ma."""
        try:
            prognoza = self.serwisy.prognoza.policz()
        except ZaMaloDanych as blad:
            self._opis_prognozy.configure(text=str(blad))
            for kafelek in self.kafelki:
                kafelek.ustaw("-")
            return
        self._opis_prognozy.configure(
            text=f"Do {formatuj_date(prognoza.koniec)} zostało dni: {prognoza.dni}. "
            f"Transakcje cykliczne: {formatuj_kwote(prognoza.cykliczne)}. "
            f"Średnie wydatki dzienne: {formatuj_kwote(prognoza.tempo_srednie)}."
        )
        wartosci = (prognoza.optymistyczna, prognoza.realistyczna, prognoza.pesymistyczna)
        for kafelek, kwota in zip(self.kafelki, wartosci):
            kafelek.ustaw(formatuj_kwote(kwota), styl.ZLY if kwota < 0 else styl.TEKST)

    def zapisz_png(self) -> None:
        """Zapisuje pokazywany wykres w wybranym miejscu."""
        if self.wykres.rysunek is None:
            raise BladPliku("Nie ma wykresu do zapisania.")
        sciezka = filedialog.asksaveasfilename(
            parent=self.okno,
            defaultextension=".png",
            filetypes=[("Obraz PNG", "*.png")],
            initialfile=f"{self.rodzaj.get().lower()}.png",
        )
        if sciezka:
            wykresy.zapisz(self.wykres.rysunek, Path(sciezka))
            self.okno.powiadom(f"Zapisano wykres: {sciezka}")
