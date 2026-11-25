"""Zakładka budżetów."""

from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from skarbonka.gui import ikony, styl
from skarbonka.gui.formularz import Formularz, Pole
from skarbonka.gui.pole_kategorii import pole_kategorii
from skarbonka.gui.skladniki import (
    Karta,
    Przewijana,
    WyborMiesiaca,
    etykieta,
    kafelek_ikony,
    pasek_postepu,
    przycisk,
    przycisk_ikony,
    pusty_stan,
    ramka,
    wyczysc,
)
from skarbonka.models.enums import StanBudzetu
from skarbonka.models.transakcja import Wydatek
from skarbonka.services.planowanie import WykonanieBudzetu
from skarbonka.utils.formatowanie import formatuj_kwote, formatuj_procent
from skarbonka.utils.walidacja import parsuj_kwote

if TYPE_CHECKING:
    from skarbonka.gui.okno import Okno

WYGLAD = {
    StanBudzetu.W_NORMIE: (styl.AKCENT_TEKST, styl.AKCENT_TLO),
    StanBudzetu.UWAGA: (styl.UWAGA, styl.UWAGA_TLO),
    StanBudzetu.PRZEKROCZONY: (styl.ZLY, styl.ZLY_TLO),
}
KOLUMNY = 2


class ZakladkaBudzety(ctk.CTkFrame):
    """Limity wydatków w kategoriach."""

    def __init__(self, rodzic: Any, okno: "Okno") -> None:
        super().__init__(rodzic, fg_color=styl.PRZEZROCZYSTY)
        self.okno = okno
        self.serwis = okno.serwisy.budzety
        gora = ramka(self)
        gora.pack(fill="x", pady=(0, 16))
        self.miesiac = WyborMiesiaca(gora, self.odswiez)
        self.miesiac.pack(side="left")
        przycisk(gora, "Ustaw limit", self.ustaw, "glowny", 110).pack(side="right")
        przycisk(gora, "Skopiuj z poprzedniego", self.skopiuj).pack(side="right", padx=10)
        self._lista = Przewijana(self)
        self._lista.pack(fill="both", expand=True)
        self._lista.grid_columnconfigure(tuple(range(KOLUMNY)), weight=1, uniform="budzety")

    def odswiez(self) -> None:
        """Wypisuje budżety wybranego miesiąca."""
        wyczysc(self._lista)
        wykonanie = self.serwis.wykonanie(self.miesiac.miesiac)
        if not wykonanie:
            pusty_stan(
                self._lista,
                ikony.KOLO,
                "Brak limitów w tym miesiącu",
                "Ustaw limit dla kategorii, a Skarbonka ostrzeże przed przekroczeniem.",
                ("Ustaw limit", self.ustaw),
            ).grid(row=0, column=0, columnspan=KOLUMNY, pady=70)
        for numer, w in enumerate(wykonanie):
            self._utworz_karte(w).grid(
                row=numer // KOLUMNY,
                column=numer % KOLUMNY,
                sticky="nsew",
                padx=(0 if numer % KOLUMNY == 0 else 16, 0),
                pady=(0, 16),
            )

    def _utworz_karte(self, w: WykonanieBudzetu) -> Karta:
        """Tworzy kartę jednego budżetu."""
        kolor, tlo = WYGLAD[w.stan]
        karta = Karta(self._lista)
        gora = ramka(karta)
        gora.pack(fill="x", padx=20, pady=(18, 14))
        kafelek_ikony(gora, ikony.dla_nazwy(w.kategoria), tlo, kolor).pack(side="left")
        napisy = ramka(gora)
        napisy.pack(side="left", padx=14)
        etykieta(napisy, w.kategoria, 15, "mocny").pack(anchor="w")
        etykieta(napisy, str(w.stan), 12, kolor=kolor).pack(anchor="w")
        przycisk_ikony(gora, ikony.KOSZ, lambda: self.usun(w)).pack(side="right")
        etykieta(gora, formatuj_procent(w.procent), 20, "liczby", kolor).pack(
            side="right", padx=8
        )
        pasek_postepu(karta, w.procent, kolor, tlo).pack(fill="x", padx=20)
        dol = ramka(karta)
        dol.pack(fill="x", padx=20, pady=(12, 18))
        etykieta(
            dol,
            f"{formatuj_kwote(w.wydano)} z {formatuj_kwote(w.budzet.limit)}",
            kolor=styl.TEKST_DRUGI,
        ).pack(side="left")
        zostalo = w.budzet.limit - w.wydano
        napis = "zostało" if zostalo >= 0 else "ponad limit"
        etykieta(dol, f"{napis} {formatuj_kwote(abs(zostalo))}", 13, "mocny", kolor).pack(
            side="right"
        )
        return karta

    def ustaw(self) -> Formularz:
        """Otwiera panel limitu."""
        miesiac = self.miesiac.miesiac

        def zapisz(dane: dict[str, Any]) -> None:
            self.serwis.ustaw(dane["kategoria"].id, miesiac, dane["limit"])
            self.okno.powiadom(f"Ustawiono limit: {dane['kategoria']}.")

        pola = [
            Pole("limit", "Limit na miesiąc", parsuj_kwote, rodzaj="kwota"),
            pole_kategorii(self.okno, Wydatek),
        ]
        return Formularz(self.okno, "Limit miesięczny", pola, zapisz)

    def skopiuj(self) -> None:
        """Kopiuje limity z poprzedniego miesiąca."""
        liczba = self.serwis.skopiuj_poprzedni(self.miesiac.miesiac)
        self.okno.powiadom(f"Skopiowane budżety: {liczba}")
        self.okno.odswiez()

    def usun(self, w: WykonanieBudzetu) -> None:
        """Usuwa budżet po potwierdzeniu."""
        if self.okno.zapytaj(f"Usunąć limit „{w.kategoria}”?", "Usuń", grozne=True):
            self.serwis.usun(w.budzet)
            self.okno.odswiez()
