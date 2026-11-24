"""Ustawienia w zakładkach oraz próg ostrzeżeń."""

from dataclasses import replace
from typing import Any

from skarbonka.gui import ikony
from skarbonka.gui.formularz import Formularz, Pole
from skarbonka.gui.skladniki import Zakladki, przycisk
from skarbonka.gui.widok import Widok
from skarbonka.gui.zakladki_ustawien import (
    ZakladkaKategorie,
    ZakladkaKonta,
    ZakladkaProfile,
    ZakladkaReguly,
)
from skarbonka.utils.walidacja import parsuj_liczbe

ZAKLADKI = (
    ("Konta", ZakladkaKonta),
    ("Kategorie", ZakladkaKategorie),
    ("Reguły", ZakladkaReguly),
    ("Profile CSV", ZakladkaProfile),
)


class WidokUstawienia(Widok):
    """Konta, kategorie, reguły i profile."""

    TYTUL = "Ustawienia"
    IKONA = ikony.USTAWIENIA

    def buduj(self) -> None:
        przycisk(self.pasek, "Próg ostrzeżeń", self.zmien_prog, "zwykly", 120).pack(
            side="right", padx=(10, 0)
        )
        self.karty = Zakladki(self.tresc, self.pasek)
        self.karty.pack(fill="both", expand=True)
        self.zakladki = {}
        for nazwa, klasa in ZAKLADKI:
            zakladka = klasa(self.karty.add(nazwa), self.okno)
            zakladka.pack(fill="both", expand=True)
            self.zakladki[nazwa] = zakladka
        self.karty.gotowe()

    def odswiez(self) -> None:
        prog = self.serwisy.ustawienia.wczytaj().prog_ostrzezen
        self.podtytul.configure(text=f"Ostrzeżenie o budżecie od {prog}% limitu")
        for zakladka in self.zakladki.values():
            zakladka.odswiez()

    def zmien_prog(self) -> Formularz:
        """Zmienia procent budżetu, od którego pojawia się ostrzeżenie."""
        serwis = self.serwisy.ustawienia
        obecne = serwis.wczytaj()

        def zapisz(dane: dict[str, Any]) -> None:
            serwis.zapisz(replace(obecne, prog_ostrzezen=dane["prog"]))
            self.okno.powiadom(f"Próg ostrzeżeń: {dane['prog']}%")

        pole = Pole(
            "prog",
            "Procent limitu, od którego ostrzegać",
            lambda tekst: parsuj_liczbe(tekst, maks=100, minimum=1),
            str(obecne.prog_ostrzezen),
        )
        return Formularz(self.okno, "Próg ostrzeżeń", [pole], zapisz)
