"""Analizy: wykresy i prognoza."""

import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, font
from typing import Any

import customtkinter as ctk

from skarbonka.gui import ikony, styl
from skarbonka.gui.pozycje import kwota_ze_znakiem
from skarbonka.gui.skladniki import (
    Karta,
    WyborMiesiaca,
    Wykres,
    etykieta,
    przycisk,
    ramka,
    segment,
)
from skarbonka.gui.widok import Widok
from skarbonka.services import analizy, wykresy
from skarbonka.services.prognoza import Prognoza
from skarbonka.utils.formatowanie import formatuj_date, formatuj_kwote
from skarbonka.wyjatki import BladPliku, ZaMaloDanych

KATEGORIE, TREND, SALDO = "Kategorie", "Trend", "Saldo"
OPISY = {
    KATEGORIE: "Na co poszły pieniądze w wybranym miesiącu",
    TREND: "Przychody i wydatki z ostatnich 6 miesięcy",
    SALDO: "Łączne saldo kont z ostatnich 90 dni",
}


class ZakresPrognozy(ctk.CTkFrame):
    """Oś od wariantu pesymistycznego do optymistycznego."""

    def __init__(self, rodzic: Any) -> None:
        super().__init__(rodzic, fg_color=styl.KARTA)
        self._skala = styl.skala(self)
        self._prognoza: Prognoza | None = None
        self._mala = font.Font(
            root=self, family=styl.rodzina("tresc"), size=-round(12 * self._skala)
        )
        self._liczby = font.Font(
            root=self, family=styl.rodzina("liczby"), size=-round(15 * self._skala)
        )
        self.plotno = tk.Canvas(
            self, highlightthickness=0, height=round(74 * self._skala), width=200
        )
        self.plotno.pack(fill="both", expand=True)
        self.plotno.bind("<Configure>", lambda _: self._rysuj())

    def pokaz(self, prognoza: Prognoza) -> None:
        """Rysuje podaną prognozę."""
        self._prognoza = prognoza
        self._rysuj()

    def _rysuj(self) -> None:
        plotno = self.plotno
        plotno.delete("all")
        plotno.configure(bg=styl.wybierz(styl.KARTA))
        if self._prognoza is None:
            return
        s = self._skala
        lewa, prawa, y = 12 * s, plotno.winfo_width() - 12 * s, 18 * s
        niska, wysoka = self._prognoza.pesymistyczna, self._prognoza.optymistyczna
        zakres = float(wysoka - niska) or 1.0
        x = lewa + (prawa - lewa) * float(self._prognoza.realistyczna - niska) / zakres
        grubosc = 8 * s
        for x0, x1, kolor in (
            (lewa, prawa, styl.WGLEBIENIE),
            (lewa, x, styl.AKCENT_TEKST),
        ):
            plotno.create_line(
                x0, y, x1, y, width=grubosc, capstyle="round", fill=styl.wybierz(kolor)
            )
        r = 9 * s
        plotno.create_oval(
            x - r,
            y - r,
            x + r,
            y + r,
            fill=styl.wybierz(styl.AKCENT_TEKST),
            outline=styl.wybierz(styl.KARTA),
            width=3 * s,
        )
        opisy = (
            (lewa, "w", "jak w najdroższym miesiącu", niska),
            (prawa, "e", "jak w najtańszym miesiącu", wysoka),
        )
        for polozenie, strona, opis, kwota in opisy:
            plotno.create_text(
                polozenie,
                y + 24 * s,
                anchor=strona,
                text=kwota_ze_znakiem(formatuj_kwote(kwota)),
                font=self._liczby,
                fill=styl.wybierz(styl.TEKST),
            )
            plotno.create_text(
                polozenie,
                y + 44 * s,
                anchor=strona,
                text=opis,
                font=self._mala,
                fill=styl.wybierz(styl.TEKST_DRUGI),
            )


class WidokAnalizy(Widok):
    """Wykresy z wybranego miesiąca i prognoza."""

    TYTUL = "Analizy"
    IKONA = ikony.WYKRES

    def buduj(self) -> None:
        przycisk(self.pasek, "Zapisz PNG", self.zapisz_png, "zwykly", 110).pack(
            side="right", padx=(10, 0)
        )
        self.rodzaj = segment(self.pasek, [KATEGORIE, TREND, SALDO], lambda _: self.odswiez())
        self.rodzaj.pack(side="right")
        self._buduj_prognoze()
        karta = Karta(self.tresc)
        karta.pack(fill="both", expand=True)
        self.miesiac = WyborMiesiaca(karta, self.odswiez)
        self.wykres = Wykres(karta)
        self.wykres.pack(side="bottom", fill="both", expand=True, padx=16, pady=(8, 16))

    def _buduj_prognoze(self) -> None:
        """Tworzy kartę prognozy na dole."""
        karta = Karta(self.tresc)
        karta.pack(side="bottom", fill="x", pady=(20, 0))
        lewa = ramka(karta)
        lewa.pack(side="left", padx=(24, 10), pady=20)
        self._tytul_prognozy = etykieta(lewa, "", 13, "mocny", styl.TEKST_DRUGI)
        self._tytul_prognozy.pack(anchor="w")
        self.prognoza = etykieta(lewa, "", 32, "liczby")
        self.prognoza.pack(anchor="w", pady=(4, 4))
        self._opis_prognozy = etykieta(lewa, "", 12, kolor=styl.TEKST_DRUGI)
        self._opis_prognozy.pack(anchor="w")
        self._zakres = ZakresPrognozy(karta)
        self._zakres.pack(side="right", fill="x", expand=True, padx=(20, 24), pady=20)

    def odswiez(self) -> None:
        rodzaj = self.rodzaj.get()
        self.podtytul.configure(text=OPISY[rodzaj])
        if rodzaj == KATEGORIE:
            self.miesiac.pack(side="top", anchor="w", padx=20, pady=(18, 0))
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
            self._tytul_prognozy.configure(text="Prognoza salda")
            self.prognoza.configure(text="-")
            self._opis_prognozy.configure(text=str(blad))
            return
        self._tytul_prognozy.configure(text=f"Prognoza na {formatuj_date(prognoza.koniec)}")
        self.prognoza.configure(text=kwota_ze_znakiem(formatuj_kwote(prognoza.realistyczna)))
        self._opis_prognozy.configure(
            text=f"Zostało dni: {prognoza.dni}, średnio "
            f"{formatuj_kwote(prognoza.tempo_srednie)} dziennie"
        )
        self._zakres.pokaz(prognoza)

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
            self.okno.powiadom(f"Zapisano wykres: {Path(sciezka).name}")
