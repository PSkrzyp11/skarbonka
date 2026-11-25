"""Pulpit: saldo, bieżący miesiąc, ostatnie transakcje i sprawy do załatwienia."""

from datetime import date
from typing import Any

import customtkinter as ctk

from skarbonka.gui import ikony, styl
from skarbonka.gui.formularze_transakcji import nowa_transakcja
from skarbonka.gui.lista import Lista
from skarbonka.gui.pozycje import kwota_ze_znakiem, pozycje_transakcji
from skarbonka.gui.skladniki import (
    Karta,
    Przewijana,
    Wykres,
    etykieta,
    kafelek_ikony,
    pasek_postepu,
    przycisk,
    pusty_stan,
    ramka,
    wyczysc,
)
from skarbonka.gui.widok import Widok
from skarbonka.models.transakcja import Wydatek
from skarbonka.services import analizy, wykresy
from skarbonka.services.transakcje import posortuj
from skarbonka.services.uwagi import PLAN, zbierz_uwagi
from skarbonka.utils.formatowanie import (
    formatuj_date,
    formatuj_dzien,
    formatuj_kwote,
    formatuj_miesiac,
    formatuj_procent,
)
from skarbonka.wyjatki import ZaMaloDanych

ILE_OSTATNICH = 5
SZEROKOSC_BOCZNA = 370


class WidokPulpit(Widok):
    """Strona startowa."""

    TYTUL = "Pulpit"
    IKONA = ikony.DOM

    def buduj(self) -> None:
        przycisk(
            self.pasek,
            "Nowa transakcja",
            lambda: nowa_transakcja(self.okno, Wydatek),
            "glowny",
            160,
            42,
        ).pack()
        self._siatka = ramka(self.tresc)
        self._siatka.grid_columnconfigure(0, weight=1)
        self._siatka.grid_columnconfigure(1, minsize=SZEROKOSC_BOCZNA)
        self._siatka.grid_rowconfigure(1, weight=1)
        self._buduj_saldo()
        self._miesiac = Karta(self._siatka, "Ten miesiąc")
        self._miesiac.grid(row=0, column=1, sticky="nsew", padx=(20, 0))
        self._tresc_miesiaca = ramka(self._miesiac)
        self._tresc_miesiaca.pack(fill="both", expand=True, padx=20, pady=(2, 18))

        ostatnie = Karta(self._siatka, "Ostatnie transakcje")
        ostatnie.grid(row=1, column=0, sticky="nsew", pady=(20, 0))
        przycisk(
            ostatnie.gora, "Wszystkie", lambda: self.okno.pokaz_widok("Transakcje"), "cichy", 80, 28
        ).pack(side="right")
        self.tabela = Lista(ostatnie)
        self.tabela.pack(fill="both", expand=True, padx=8, pady=(0, 12))

        sprawy = Karta(self._siatka, "Do załatwienia")
        sprawy.grid(row=1, column=1, sticky="nsew", padx=(20, 0), pady=(20, 0))
        self._sprawy = Przewijana(sprawy, styl.KARTA)
        self._sprawy.pack(fill="both", expand=True, padx=(12, 6), pady=(0, 12))
        self._pusty = pusty_stan(
            self.tresc,
            ikony.KARTA,
            "Zacznij od pierwszej transakcji",
            "Saldo, wykresy i prognoza pojawią się same.",
            ("Dodaj transakcję", lambda: nowa_transakcja(self.okno, Wydatek)),
        )

    def _buduj_saldo(self) -> None:
        """Tworzy zieloną kartę z saldem i wykresem."""
        karta = ctk.CTkFrame(self._siatka, fg_color=styl.MARKA, corner_radius=20, height=270)
        karta.grid(row=0, column=0, sticky="nsew")
        karta.pack_propagate(False)
        gora = ramka(karta)
        gora.pack(fill="x", padx=28, pady=(24, 0))
        etykieta(gora, "Łączne saldo", 13, "mocny", styl.MARKA_TEKST).pack(anchor="w")
        self.saldo = etykieta(gora, "", 46, "liczby", styl.BIALY)
        self.saldo.pack(anchor="w", pady=(4, 6))
        zmiana = ramka(gora)
        zmiana.pack(anchor="w")
        self._strzalka = etykieta(zmiana, "", 13, "ikony", styl.MOSIADZ)
        self._strzalka.pack(side="left", padx=(0, 6))
        self._zmiana = etykieta(zmiana, "", 13, kolor=styl.MARKA_TEKST)
        self._zmiana.pack(side="left")
        self.wykres = Wykres(karta, styl.MARKA)
        self.wykres.pack(fill="both", expand=True, padx=14, pady=(4, 14))

    def odswiez(self) -> None:
        dzis = date.today()
        self.podtytul.configure(text=formatuj_dzien(dzis, z_wzgledna=False))
        transakcje = self.serwisy.transakcje.wszystkie()
        if not transakcje:
            self._siatka.pack_forget()
            self._pusty.pack(expand=True)
            return
        self._pusty.pack_forget()
        self._siatka.pack(fill="both", expand=True)
        sumy = analizy.podsumowanie_miesiaca(transakcje, dzis)
        saldo = self.serwisy.konta.saldo()
        bilans = sumy["Bilans"]
        self.saldo.configure(text=kwota_ze_znakiem(formatuj_kwote(saldo)))
        self._strzalka.configure(text=ikony.W_DOL if bilans < 0 else ikony.W_GORE)
        self._zmiana.configure(
            text=f"{kwota_ze_znakiem(formatuj_kwote(bilans))} w tym miesiącu"
        )
        historia = analizy.historia_salda(transakcje, saldo, dzis)
        self.wykres.pokaz(
            wykresy.rysuj_saldo(historia, paleta=styl.paleta_marki(), uproszczony=True)
        )
        ostatnie = posortuj(transakcje)[:ILE_OSTATNICH]
        self.tabela.wypelnij(pozycje_transakcji(ostatnie, self.serwisy, z_data=True))
        self._pokaz_miesiac(sumy)
        self._pokaz_sprawy()

    def _pokaz_miesiac(self, sumy: dict) -> None:
        """Wypełnia kartę bieżącego miesiąca."""
        wyczysc(self._tresc_miesiaca)
        self._miesiac.tytul.configure(text=formatuj_miesiac(date.today()).capitalize())
        najwiecej = max(sumy["Przychody"], sumy["Wydatki"], 1)
        for nazwa, kolor in (("Przychody", styl.AKCENT_TEKST), ("Wydatki", styl.MOSIADZ)):
            rzad = ramka(self._tresc_miesiaca)
            rzad.pack(fill="x", pady=(6, 4))
            etykieta(rzad, nazwa, kolor=styl.TEKST_DRUGI).pack(side="left")
            etykieta(rzad, formatuj_kwote(sumy[nazwa]), 17, "liczby").pack(side="right")
            procent = float(sumy[nazwa] / najwiecej * 100)
            pasek_postepu(self._tresc_miesiaca, procent, kolor).pack(fill="x", pady=(0, 6))
        stopa = analizy.stopa_oszczednosci(sumy["Przychody"], sumy["Bilans"])
        self._dodaj_linie("Oszczędności", "-" if stopa is None else formatuj_procent(stopa))
        bilans = self.serwisy.cykliczne.bilans()
        if bilans.przychody or bilans.wydatki:
            self._dodaj_linie(
                "Na czysto co miesiąc", kwota_ze_znakiem(formatuj_kwote(bilans.na_czysto))
            )
        try:
            prognoza = self.serwisy.prognoza.policz()
        except ZaMaloDanych:
            self._dodaj_linie("Prognoza", "za krótka historia")
            return
        self._dodaj_linie(
            f"Prognoza na {formatuj_date(prognoza.koniec)[:5]}",
            kwota_ze_znakiem(formatuj_kwote(prognoza.realistyczna)),
        )

    def _dodaj_linie(self, nazwa: str, wartosc: str) -> None:
        """Dodaje wiersz oddzielony linią."""
        ctk.CTkFrame(
            self._tresc_miesiaca, height=2, fg_color=styl.LINIA, corner_radius=0
        ).pack(fill="x", pady=10)
        rzad = ramka(self._tresc_miesiaca)
        rzad.pack(fill="x")
        etykieta(rzad, nazwa, kolor=styl.TEKST_DRUGI).pack(side="left")
        etykieta(rzad, wartosc, 17, "liczby").pack(side="right")

    def _pokaz_sprawy(self) -> None:
        """Wypisuje ostrzeżenia. Kliknięcie prowadzi do właściwego działu."""
        wyczysc(self._sprawy)
        uwagi = zbierz_uwagi(self.serwisy)
        for uwaga in uwagi:
            self._dodaj_sprawe(
                ikony.OSTRZEZENIE, uwaga.tekst, styl.UWAGA_TLO, styl.UWAGA, uwaga.dzial
            )
        if not uwagi:
            self._dodaj_sprawe(
                ikony.GOTOWE, "Wszystko w porządku.", styl.AKCENT_TLO, styl.AKCENT_TEKST
            )

    def _dodaj_sprawe(
        self, ikona: str, tekst: str, tlo: styl.Kolor, kolor: styl.Kolor, dzial: str = PLAN
    ) -> None:
        """Dodaje jedną sprawę."""
        rzad = ramka(self._sprawy)
        rzad.pack(fill="x", pady=5)
        kafelek_ikony(rzad, ikona, tlo, kolor, bok=36).pack(side="left", padx=(4, 12))
        napis = etykieta(rzad, tekst)
        napis.configure(wraplength=SZEROKOSC_BOCZNA - 120)
        napis.pack(side="left", fill="x")
        self._podepnij(dzial, rzad, napis)

    def _podepnij(self, dzial: str, *elementy: Any) -> None:
        for element in elementy:
            element.configure(cursor="hand2")
            element.bind("<Button-1>", lambda _: self.okno.pokaz_widok(dzial))
