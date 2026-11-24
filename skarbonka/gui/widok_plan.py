"""Plan: budżety, cele i transakcje cykliczne w zakładkach."""

from skarbonka.gui import styl
from skarbonka.gui.skladniki import zakladki
from skarbonka.gui.widok import Widok
from skarbonka.gui.zakladka_budzety import ZakladkaBudzety
from skarbonka.gui.zakladka_cele import ZakladkaCele
from skarbonka.gui.zakladka_cykliczne import ZakladkaCykliczne

ZAKLADKI = (
    ("Budżety", ZakladkaBudzety),
    ("Cele", ZakladkaCele),
    ("Cykliczne", ZakladkaCykliczne),
)


class WidokPlan(Widok):
    """Planowanie wydatków."""

    TYTUL = "Plan"

    def buduj(self) -> None:
        self.karty = zakladki(self.tresc)
        self.karty.pack(fill="both", expand=True)
        self.zakladki = {}
        for nazwa, klasa in ZAKLADKI:
            zakladka = klasa(self.karty.add(nazwa), self.okno)
            zakladka.configure(fg_color=styl.PRZEZROCZYSTY)
            zakladka.pack(fill="both", expand=True)
            self.zakladki[nazwa] = zakladka

    def odswiez(self) -> None:
        for zakladka in self.zakladki.values():
            zakladka.odswiez()
