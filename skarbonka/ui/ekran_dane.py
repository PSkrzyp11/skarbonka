"""Ekran danych: wymiana danych z plikami."""

from datetime import datetime
from pathlib import Path

from skarbonka.config import KATALOG_EKSPORTU
from skarbonka.services.transakcje import posortuj
from skarbonka.ui import widoki
from skarbonka.ui.menu import Ekran, OpcjaMenu
from skarbonka.ui.wejscie import potwierdz, wczytaj_sciezke


class EkranDanych(Ekran):
    """Eksport danych."""

    TYTUL = "Dane"

    def opcje(self) -> list[OpcjaMenu]:
        return [
            OpcjaMenu("Eksport transakcji do CSV", self.eksportuj),
        ]

    def eksportuj(self) -> None:
        """Zapisuje wszystkie transakcje do wybranego pliku."""
        transakcje = posortuj(self.serwisy.transakcje.wszystkie(), "od najstarszych")
        if not transakcje:
            print("Brak transakcji do eksportu.")
            return
        nazwa = f"transakcje-{datetime.now():%Y%m%d-%H%M%S}.csv"
        sciezka = wczytaj_sciezke("Plik docelowy", KATALOG_EKSPORTU / nazwa)
        if self._mozna_zapisac(sciezka):
            self.serwisy.eksporter.zapisz(transakcje, sciezka)
            widoki.sukces(f"Zapisano {len(transakcje)} transakcji: {sciezka}")

    @staticmethod
    def _mozna_zapisac(sciezka: Path) -> bool:
        """Pyta o zgodę, jeśli plik już istnieje."""
        return not sciezka.exists() or potwierdz("Plik już istnieje. Nadpisać?")
