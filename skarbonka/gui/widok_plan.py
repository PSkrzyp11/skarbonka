"""Plan: budżety, cele i transakcje cykliczne."""

from skarbonka.gui import ikony
from skarbonka.gui.skladniki import Zakladki
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
    IKONA = ikony.KALENDARZ

    def buduj(self) -> None:
        self.podtytul.configure(text="Limity, oszczędzanie i stałe płatności")
        self.karty = Zakladki(self.tresc, self.pasek)
        self.karty.pack(fill="both", expand=True)
        self.zakladki = {}
        for nazwa, klasa in ZAKLADKI:
            zakladka = klasa(self.karty.add(nazwa), self.okno)
            zakladka.pack(fill="both", expand=True)
            self.zakladki[nazwa] = zakladka
        self.karty.gotowe()

    def odswiez(self) -> None:
        for zakladka in self.zakladki.values():
            zakladka.odswiez()
