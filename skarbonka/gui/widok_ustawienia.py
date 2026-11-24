"""Ustawienia w zakładkach oraz próg ostrzeżeń."""

from dataclasses import replace
from typing import Any

from skarbonka.gui.formularz import Formularz, Pole
from skarbonka.gui.skladniki import przycisk, zakladki
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

    def buduj(self) -> None:
        przycisk(self.pasek, "Próg ostrzeżeń budżetu", self.zmien_prog).pack()
        self.karty = zakladki(self.tresc)
        self.karty.pack(fill="both", expand=True)
        self.zakladki = {}
        for nazwa, klasa in ZAKLADKI:
            zakladka = klasa(self.karty.add(nazwa), self.okno)
            zakladka.pack(fill="both", expand=True)
            self.zakladki[nazwa] = zakladka

    def odswiez(self) -> None:
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
            "Próg w procentach",
            lambda tekst: parsuj_liczbe(tekst, maks=100, minimum=1),
            str(obecne.prog_ostrzezen),
        )
        return Formularz(self.okno, "Próg ostrzeżeń budżetu", [pole], zapisz)
