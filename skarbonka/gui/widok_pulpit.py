"""Pulpit: najważniejsze liczby, wykres salda i sprawy do załatwienia."""

from datetime import date

import customtkinter as ctk

from skarbonka.gui import styl
from skarbonka.gui.formularze_transakcji import nowa_transakcja
from skarbonka.gui.skladniki import Kafelek, Karta, Tabela, Wykres, etykieta, przycisk, wyczysc
from skarbonka.gui.widok import Widok
from skarbonka.gui.wiersze import KOLUMNY_TRANSAKCJI, wiersze_transakcji
from skarbonka.models.transakcja import Przychod, Wydatek
from skarbonka.services import analizy, wykresy
from skarbonka.services.transakcje import posortuj
from skarbonka.services.uwagi import zbierz_uwagi
from skarbonka.utils.formatowanie import formatuj_kwote, formatuj_procent
from skarbonka.wyjatki import ZaMaloDanych

ILE_OSTATNICH = 6
SZEROKOSC_UWAG = 290


class WidokPulpit(Widok):
    """Strona startowa."""

    TYTUL = "Pulpit"

    def buduj(self) -> None:
        przycisk(
            self.pasek, "+ Wydatek", lambda: nowa_transakcja(self.okno, Wydatek), glowny=True
        ).pack(side="left", padx=(0, 8))
        przycisk(self.pasek, "+ Przychód", lambda: nowa_transakcja(self.okno, Przychod)).pack(
            side="left"
        )
        self._buduj_kafelki()
        dol = Karta(self.tresc, "Ostatnie transakcje")
        dol.pack(side="bottom", fill="x")
        self.tabela = Tabela(dol, KOLUMNY_TRANSAKCJI, wysokosc=ILE_OSTATNICH)
        self.tabela.pack(fill="x", padx=10, pady=(0, 10))

        srodek = ctk.CTkFrame(self.tresc, fg_color=styl.PRZEZROCZYSTY)
        srodek.pack(fill="both", expand=True, pady=14)
        srodek.grid_columnconfigure(0, weight=1)
        srodek.grid_rowconfigure(0, weight=1)

        karta = Karta(srodek, "Łączne saldo, 90 dni")
        karta.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self.wykres = Wykres(karta)
        self.wykres.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        prawa = Karta(srodek, "Wymaga uwagi")
        prawa.grid(row=0, column=1, sticky="nsew")
        self._uwagi = ctk.CTkFrame(prawa, fg_color=styl.PRZEZROCZYSTY, width=SZEROKOSC_UWAG)
        self._uwagi.pack(fill="both", expand=True, padx=16, pady=(0, 12))

    def _buduj_kafelki(self) -> None:
        """Tworzy rząd kafelków z liczbami."""
        rzad = ctk.CTkFrame(self.tresc, fg_color=styl.PRZEZROCZYSTY)
        rzad.pack(fill="x")
        nazwy = ("Łączne saldo", "Przychody w miesiącu", "Wydatki w miesiącu", "Oszczędności")
        self.kafelki = [Kafelek(rzad, nazwa) for nazwa in nazwy]
        for i, kafelek in enumerate(self.kafelki):
            rzad.grid_columnconfigure(i, weight=1, uniform="kafelki")
            kafelek.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 14, 0))

    def odswiez(self) -> None:
        dzis = date.today()
        transakcje = self.serwisy.transakcje.wszystkie()
        sumy = analizy.podsumowanie_miesiaca(transakcje, dzis)
        saldo = self.serwisy.konta.saldo()
        stopa = analizy.stopa_oszczednosci(sumy["Przychody"], sumy["Bilans"])
        wartosci = (
            (formatuj_kwote(saldo), styl.ZLY if saldo < 0 else styl.TEKST),
            (formatuj_kwote(sumy["Przychody"]), styl.DOBRY),
            (formatuj_kwote(sumy["Wydatki"]), styl.ZLY),
            ("-" if stopa is None else formatuj_procent(stopa), styl.TEKST),
        )
        for kafelek, (tekst, kolor) in zip(self.kafelki, wartosci):
            kafelek.ustaw(tekst, kolor)

        if transakcje:
            historia = analizy.historia_salda(transakcje, saldo, dzis)
            self.wykres.pokaz(wykresy.rysuj_saldo(historia, paleta=styl.paleta()))
        else:
            self.wykres.pusty("Dodaj pierwszą transakcję, aby zobaczyć wykres.")
        self.tabela.wypelnij(
            wiersze_transakcji(posortuj(transakcje)[:ILE_OSTATNICH], self.serwisy)
        )
        self._pokaz_uwagi()

    def _pokaz_uwagi(self) -> None:
        """Wypisuje ostrzeżenia i prognozę."""
        wyczysc(self._uwagi)
        uwagi = zbierz_uwagi(self.serwisy)
        for tekst in uwagi or ["Wszystko w porządku."]:
            kolor = styl.UWAGA if uwagi else styl.TEKST_DRUGI
            self._dodaj_napis(tekst, kolor)
        try:
            prognoza = self.serwisy.prognoza.policz()
        except ZaMaloDanych as blad:
            self._dodaj_napis(str(blad), styl.TEKST_DRUGI)
            return
        etykieta(
            self._uwagi, "Prognoza na koniec miesiąca", gruba=True, kolor=styl.TEKST_DRUGI
        ).pack(anchor="w", pady=(16, 0))
        etykieta(self._uwagi, formatuj_kwote(prognoza.realistyczna), 20, gruba=True).pack(
            anchor="w"
        )
        zakres = (prognoza.pesymistyczna, prognoza.optymistyczna)
        self._dodaj_napis(
            f"od {formatuj_kwote(zakres[0])} do {formatuj_kwote(zakres[1])}", styl.TEKST_DRUGI
        )

    def _dodaj_napis(self, tekst: str, kolor: styl.Kolor) -> None:
        """Dodaje zawijany napis do karty uwag."""
        napis = etykieta(self._uwagi, tekst, kolor=kolor)
        napis.configure(wraplength=SZEROKOSC_UWAG - 20)
        napis.pack(anchor="w", pady=3)
