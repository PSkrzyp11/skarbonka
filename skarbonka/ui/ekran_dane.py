"""Ekran danych: wymiana danych z plikami."""

from datetime import datetime
from pathlib import Path

from skarbonka.config import KATALOG_EKSPORTU
from skarbonka.services.transakcje import posortuj
from skarbonka.ui import widoki
from skarbonka.ui.menu import Ekran, OpcjaMenu
from skarbonka.ui.wejscie import potwierdz, wczytaj_sciezke, wybierz

LICZBA_W_PODGLADZIE = 5


class EkranDanych(Ekran):
    """Import i eksport danych."""

    TYTUL = "Dane"

    def opcje(self) -> list[OpcjaMenu]:
        return [
            OpcjaMenu("Import wyciągu CSV", self.importuj),
            OpcjaMenu("Eksport transakcji do CSV", self.eksportuj),
        ]

    def importuj(self) -> None:
        """Wczytuje plik, pokazuje podgląd i po zgodzie zapisuje transakcje."""
        sciezka = wczytaj_sciezke("Plik CSV")
        profil = wybierz("Profil", self.serwisy.profile.wszystkie())
        konto = wybierz("Konto", self.serwisy.konta.wszystkie())
        podglad = self.serwisy.importer.przygotuj(sciezka, profil, konto.id)
        widoki.pokaz_bledy(podglad.bledy)
        print(f"Poprawne: {len(podglad.nowe)}, błędne: {len(podglad.bledy)}")
        if not podglad.nowe:
            return
        print("Początek pliku:")
        widoki.pokaz_transakcje(
            podglad.nowe[:LICZBA_W_PODGLADZIE],
            self.serwisy.konta.nazwy(),
            self.serwisy.kategorie.nazwy(),
        )
        if potwierdz(f"Zaimportować {len(podglad.nowe)} transakcji?"):
            liczba = self.serwisy.importer.zapisz(podglad.nowe)
            widoki.sukces(f"Zaimportowano {liczba} transakcji.")

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
