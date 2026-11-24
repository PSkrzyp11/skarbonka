"""Zakładka budżetów."""

from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from skarbonka.gui import styl
from skarbonka.gui.formularz import Formularz, Pole
from skarbonka.gui.skladniki import (
    Karta,
    WyborMiesiaca,
    etykieta,
    pasek_postepu,
    przewijana,
    przycisk,
    wyczysc,
)
from skarbonka.models.enums import StanBudzetu
from skarbonka.models.transakcja import Wydatek
from skarbonka.services.planowanie import WykonanieBudzetu
from skarbonka.utils.formatowanie import formatuj_kwote, formatuj_procent
from skarbonka.utils.walidacja import parsuj_kwote

if TYPE_CHECKING:
    from skarbonka.gui.okno import Okno

KOLORY = {
    StanBudzetu.W_NORMIE: styl.DOBRY,
    StanBudzetu.UWAGA: styl.UWAGA,
    StanBudzetu.PRZEKROCZONY: styl.ZLY,
}


class ZakladkaBudzety(ctk.CTkFrame):
    """Limity wydatków w kategoriach."""

    def __init__(self, rodzic: Any, okno: "Okno") -> None:
        super().__init__(rodzic)
        self.okno = okno
        self.serwis = okno.serwisy.budzety
        gora = ctk.CTkFrame(self, fg_color=styl.PRZEZROCZYSTY)
        gora.pack(fill="x", pady=(6, 10))
        self.miesiac = WyborMiesiaca(gora, self.odswiez)
        self.miesiac.pack(side="left")
        przycisk(gora, "Ustaw limit", self.ustaw, glowny=True).pack(side="right")
        przycisk(gora, "Skopiuj z poprzedniego", self.skopiuj).pack(side="right", padx=8)
        self._lista = przewijana(self)
        self._lista.pack(fill="both", expand=True)

    def odswiez(self) -> None:
        """Wypisuje budżety wybranego miesiąca."""
        wyczysc(self._lista)
        wykonanie = self.serwis.wykonanie(self.miesiac.miesiac)
        if not wykonanie:
            etykieta(self._lista, "Brak budżetów w tym miesiącu.", kolor=styl.TEKST_DRUGI).pack(
                pady=40
            )
        for w in wykonanie:
            self._dodaj_karte(w)

    def _dodaj_karte(self, w: WykonanieBudzetu) -> None:
        """Dodaje kartę jednego budżetu."""
        karta = Karta(self._lista)
        karta.pack(fill="x", pady=(0, 10))
        gora = ctk.CTkFrame(karta, fg_color=styl.PRZEZROCZYSTY)
        gora.pack(fill="x", padx=16, pady=(12, 4))
        etykieta(gora, w.kategoria, 15, gruba=True).pack(side="left")
        przycisk(gora, "Usuń", lambda: self.usun(w), szerokosc=60).pack(side="right")
        etykieta(gora, f"{w.stan}, {formatuj_procent(w.procent)}", kolor=KOLORY[w.stan]).pack(
            side="right", padx=12
        )
        pasek_postepu(karta, w.procent, KOLORY[w.stan]).pack(fill="x", padx=16, pady=4)
        opis = f"{formatuj_kwote(w.wydano)} z {formatuj_kwote(w.budzet.limit)}"
        etykieta(karta, opis, 12, kolor=styl.TEKST_DRUGI).pack(anchor="w", padx=16, pady=(0, 10))

    def ustaw(self) -> Formularz:
        """Otwiera formularz limitu."""
        miesiac = self.miesiac.miesiac
        kategorie = {k.nazwa: k for k in self.okno.serwisy.kategorie.pasujace(Wydatek)}

        def zapisz(dane: dict[str, Any]) -> None:
            self.serwis.ustaw(dane["kategoria"].id, miesiac, dane["limit"])
            self.okno.powiadom(f"Ustawiono limit: {dane['kategoria']}.")

        pola = [
            Pole("kategoria", "Kategoria", wybor=kategorie),
            Pole("limit", "Limit w zł", parsuj_kwote),
        ]
        return Formularz(self.okno, "Limit miesięczny", pola, zapisz)

    def skopiuj(self) -> None:
        """Kopiuje limity z poprzedniego miesiąca."""
        liczba = self.serwis.skopiuj_poprzedni(self.miesiac.miesiac)
        self.okno.powiadom(f"Skopiowane budżety: {liczba}")
        self.odswiez()

    def usun(self, w: WykonanieBudzetu) -> None:
        """Usuwa budżet po potwierdzeniu."""
        if self.okno.zapytaj(f"Usunąć budżet „{w.kategoria}”?"):
            self.serwis.usun(w.budzet)
            self.odswiez()
