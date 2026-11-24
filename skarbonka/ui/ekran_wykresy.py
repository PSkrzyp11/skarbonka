"""Ekran wykresów zapisywanych do PNG."""

import webbrowser
from datetime import date, datetime
from pathlib import Path

from skarbonka.services import analizy, wykresy
from skarbonka.ui import widoki
from skarbonka.ui.menu import Ekran, OpcjaMenu
from skarbonka.ui.wejscie import potwierdz, wczytaj_miesiac


class EkranWykresow(Ekran):
    """Tworzenie i otwieranie wykresów."""

    TYTUL = "Wykresy"

    def opcje(self) -> list[OpcjaMenu]:
        return [
            OpcjaMenu("Wydatki według kategorii", self.kategorie),
            OpcjaMenu("Przychody i wydatki, 6 miesięcy", self.trend),
            OpcjaMenu("Saldo, 90 dni", self.saldo),
        ]

    def kategorie(self) -> None:
        """Rysuje wydatki wybranego miesiąca."""
        miesiac = wczytaj_miesiac()
        wybrane = analizy.z_miesiaca(self.serwisy.transakcje.wszystkie(), miesiac)
        kwoty = analizy.wydatki_wg_kategorii(wybrane, self.serwisy.kategorie.wszystkie())
        if not kwoty:
            print("Brak wydatków w tym miesiącu.")
            return
        sciezka = self._sciezka("kategorie")
        wykresy.wykres_kategorii(kwoty, miesiac, sciezka)
        self._zakoncz(sciezka)

    def trend(self) -> None:
        """Rysuje przychody i wydatki ostatnich miesięcy."""
        transakcje = self.serwisy.transakcje.wszystkie()
        if not transakcje:
            print("Brak transakcji.")
            return
        sciezka = self._sciezka("trend")
        wykresy.wykres_trendu(analizy.trend(transakcje), sciezka)
        self._zakoncz(sciezka)

    def saldo(self) -> None:
        """Rysuje zmiany łącznego salda."""
        transakcje = self.serwisy.transakcje.wszystkie()
        if not transakcje:
            print("Brak transakcji.")
            return
        historia = analizy.historia_salda(
            transakcje, self.serwisy.konta.saldo(), date.today()
        )
        sciezka = self._sciezka("saldo")
        wykresy.wykres_salda(historia, sciezka)
        self._zakoncz(sciezka)

    def _sciezka(self, nazwa: str) -> Path:
        """Zwraca ścieżkę nowego pliku z wykresem."""
        plik = f"{nazwa}-{datetime.now():%Y%m%d-%H%M%S}.png"
        return self.serwisy.katalog / "wykresy" / plik

    @staticmethod
    def _zakoncz(sciezka: Path) -> None:
        """Pokazuje ścieżkę i proponuje otwarcie pliku."""
        widoki.sukces(f"Zapisano wykres: {sciezka}")
        if potwierdz("Otworzyć wykres?"):
            webbrowser.open(sciezka.resolve().as_uri())
