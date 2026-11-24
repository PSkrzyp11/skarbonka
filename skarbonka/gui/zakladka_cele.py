"""Zakładka celów oszczędnościowych."""

from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from skarbonka.gui import ikony, styl
from skarbonka.gui.formularz import Formularz, Pole
from skarbonka.gui.skladniki import (
    Karta,
    Przewijana,
    etykieta,
    kafelek_ikony,
    pasek_postepu,
    przycisk,
    przycisk_ikony,
    pusty_stan,
    ramka,
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
        super().__init__(rodzic, fg_color=styl.PRZEZROCZYSTY)
        self.okno = okno
        self.serwis = okno.serwisy.cele
        gora = ramka(self)
        gora.pack(fill="x", pady=(0, 16))
        self._razem = etykieta(gora, "", 14, kolor=styl.TEKST_DRUGI)
        self._razem.pack(side="left")
        przycisk(gora, "Dodaj cel", self.dodaj, "glowny", 110).pack(side="right")
        self._lista = Przewijana(self)
        self._lista.pack(fill="both", expand=True)

    def odswiez(self) -> None:
        """Wypisuje cele."""
        wyczysc(self._lista)
        cele = self.serwis.wszystkie()
        odlozono = sum((cel.odlozono for cel in cele), start=0)
        self._razem.configure(text=f"Odłożono razem {formatuj_kwote(odlozono)}" if cele else "")
        if not cele:
            pusty_stan(
                self._lista,
                ikony.FLAGA,
                "Na co odkładasz?",
                "Skarbonka policzy, ile odkładać co miesiąc, żeby zdążyć.",
                ("Dodaj cel", self.dodaj),
            ).pack(pady=70)
        for cel in cele:
            self._dodaj_karte(cel)

    def _dodaj_karte(self, cel: Cel) -> None:
        """Dodaje kartę jednego celu."""
        dzis = date.today()
        osiagniety = cel.brakuje == 0
        spozniony = not osiagniety and cel.termin < dzis
        kolor, tlo = (
            (styl.ZLY, styl.ZLY_TLO) if spozniony else (styl.AKCENT_TEKST, styl.AKCENT_TLO)
        )
        karta = Karta(self._lista)
        karta.pack(fill="x", pady=(0, 16))
        gora = ramka(karta)
        gora.pack(fill="x", padx=22, pady=(20, 14))
        kafelek_ikony(
            gora, ikony.dla_nazwy(cel.nazwa, ikony.FLAGA), tlo, kolor, bok=46
        ).pack(side="left")
        napisy = ramka(gora)
        napisy.pack(side="left", padx=16)
        etykieta(napisy, cel.nazwa, 17, "mocny").pack(anchor="w")
        termin = f"termin {formatuj_date(cel.termin)}"
        etykieta(napisy, termin, 12, kolor=styl.TEKST_DRUGI).pack(anchor="w")
        przycisk_ikony(gora, ikony.KOSZ, lambda: self.usun(cel)).pack(side="right")
        przycisk(gora, "Wpłać", lambda: self.wplac(cel), "zwykly", 86).pack(side="right", padx=8)
        etykieta(gora, formatuj_procent(cel.procent), 24, "liczby", kolor).pack(
            side="right", padx=14
        )
        pasek_postepu(karta, cel.procent, kolor, tlo).pack(fill="x", padx=22)
        dol = ramka(karta)
        dol.pack(fill="x", padx=22, pady=(12, 20))
        etykieta(
            dol,
            f"{formatuj_kwote(cel.odlozono)} z {formatuj_kwote(cel.kwota_docelowa)}",
            kolor=styl.TEKST_DRUGI,
        ).pack(side="left")
        rata = "Cel osiągnięty" if osiagniety else f"{formatuj_kwote(cel.rata(dzis))} miesięcznie"
        etykieta(dol, rata, 13, "mocny", kolor).pack(side="right")

    def dodaj(self) -> Formularz:
        """Otwiera panel nowego celu."""
        jutro = date.today() + timedelta(days=1)

        def zapisz(dane: dict[str, Any]) -> None:
            self.serwis.dodaj(dane["nazwa"], dane["kwota"], dane["termin"])
            self.okno.powiadom(f"Dodano cel {dane['nazwa']}.")

        pola = [
            Pole("kwota", "Kwota docelowa", parsuj_kwote, rodzaj="kwota"),
            Pole("nazwa", "Nazwa", parser_nazwy(self.serwis.sprawdz_nazwe)),
            Pole("termin", "Termin", lambda tekst: parsuj_date(tekst, najwczesniej=jutro)),
        ]
        return Formularz(self.okno, "Nowy cel", pola, zapisz, "Dodaj cel")

    def wplac(self, cel: Cel) -> Formularz:
        """Otwiera panel wpłaty."""

        def zapisz(dane: dict[str, Any]) -> None:
            self.serwis.wplac(cel, dane["kwota"])
            self.okno.powiadom(f"Wpłacono na cel {cel.nazwa}.")

        pola = [Pole("kwota", "Kwota", parsuj_kwote, rodzaj="kwota")]
        return Formularz(self.okno, f"Wpłata: {cel.nazwa}", pola, zapisz, "Wpłać")

    def usun(self, cel: Cel) -> None:
        """Usuwa cel po potwierdzeniu."""
        if self.okno.zapytaj(f"Usunąć cel „{cel.nazwa}” i jego wpłaty?", "Usuń", grozne=True):
            self.serwis.usun(cel)
            self.okno.odswiez()
