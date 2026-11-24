"""Zakładka celów oszczędnościowych."""

from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from skarbonka.gui import styl
from skarbonka.gui.formularz import Formularz, Pole
from skarbonka.gui.skladniki import (
    Karta,
    etykieta,
    pasek_postepu,
    przewijana,
    przycisk,
    wyczysc,
)
from skarbonka.gui.zakladka_listy import parser_nazwy
from skarbonka.models.plan import Cel
from skarbonka.utils.formatowanie import formatuj_date, formatuj_kwote, formatuj_procent
from skarbonka.utils.walidacja import parsuj_date, parsuj_kwote

if TYPE_CHECKING:
    from skarbonka.gui.okno import Okno


class ZakladkaCele(ctk.CTkFrame):
    """Kwoty, które użytkownik chce odłożyć."""

    def __init__(self, rodzic: Any, okno: "Okno") -> None:
        super().__init__(rodzic)
        self.okno = okno
        self.serwis = okno.serwisy.cele
        gora = ctk.CTkFrame(self, fg_color=styl.PRZEZROCZYSTY)
        gora.pack(fill="x", pady=(6, 10))
        przycisk(gora, "Dodaj cel", self.dodaj, glowny=True).pack(side="right")
        self._lista = przewijana(self)
        self._lista.pack(fill="both", expand=True)

    def odswiez(self) -> None:
        """Wypisuje cele."""
        wyczysc(self._lista)
        cele = self.serwis.wszystkie()
        if not cele:
            etykieta(self._lista, "Brak celów.", kolor=styl.TEKST_DRUGI).pack(pady=40)
        for cel in cele:
            self._dodaj_karte(cel)

    def _dodaj_karte(self, cel: Cel) -> None:
        """Dodaje kartę jednego celu."""
        dzis = date.today()
        osiagniety = cel.brakuje == 0
        kolor = styl.DOBRY if osiagniety else styl.ZLY if cel.termin < dzis else styl.AKCENT
        karta = Karta(self._lista)
        karta.pack(fill="x", pady=(0, 10))
        gora = ctk.CTkFrame(karta, fg_color=styl.PRZEZROCZYSTY)
        gora.pack(fill="x", padx=16, pady=(12, 4))
        etykieta(gora, cel.nazwa, 15, gruba=True).pack(side="left")
        przycisk(gora, "Usuń", lambda: self.usun(cel), szerokosc=60).pack(side="right")
        przycisk(gora, "Wpłać", lambda: self.wplac(cel), szerokosc=70).pack(side="right", padx=8)
        etykieta(gora, formatuj_procent(cel.procent), gruba=True).pack(side="right", padx=8)
        pasek_postepu(karta, cel.procent, kolor).pack(fill="x", padx=16, pady=4)
        opis = (
            f"{formatuj_kwote(cel.odlozono)} z {formatuj_kwote(cel.kwota_docelowa)}, "
            f"termin {formatuj_date(cel.termin)}, "
        )
        opis += "cel osiągnięty" if osiagniety else f"{formatuj_kwote(cel.rata(dzis))} miesięcznie"
        etykieta(karta, opis, 12, kolor=styl.TEKST_DRUGI).pack(anchor="w", padx=16, pady=(0, 10))

    def dodaj(self) -> Formularz:
        """Otwiera formularz nowego celu."""
        jutro = date.today() + timedelta(days=1)

        def zapisz(dane: dict[str, Any]) -> None:
            self.serwis.dodaj(dane["nazwa"], dane["kwota"], dane["termin"])
            self.okno.powiadom(f"Dodano cel {dane['nazwa']}.")

        pola = [
            Pole("nazwa", "Nazwa", parser_nazwy(self.serwis.sprawdz_nazwe)),
            Pole("kwota", "Kwota docelowa w zł", parsuj_kwote),
            Pole("termin", "Termin", lambda tekst: parsuj_date(tekst, najwczesniej=jutro)),
        ]
        return Formularz(self.okno, "Nowy cel", pola, zapisz, "Dodaj")

    def wplac(self, cel: Cel) -> Formularz:
        """Otwiera formularz wpłaty."""

        def zapisz(dane: dict[str, Any]) -> None:
            self.serwis.wplac(cel, dane["kwota"])
            self.okno.powiadom(f"Wpłacono na cel {cel.nazwa}.")

        pola = [Pole("kwota", "Kwota w zł", parsuj_kwote)]
        return Formularz(self.okno, f"Wpłata: {cel.nazwa}", pola, zapisz, "Wpłać")

    def usun(self, cel: Cel) -> None:
        """Usuwa cel po potwierdzeniu."""
        if self.okno.zapytaj(f"Usunąć cel „{cel.nazwa}” i jego wpłaty?"):
            self.serwis.usun(cel)
            self.odswiez()
