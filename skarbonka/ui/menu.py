"""Uniwersalne menu tekstowe."""

from collections.abc import Callable
from dataclasses import dataclass

from skarbonka.ui.wejscie import wczytaj_wybor
from skarbonka.wyjatki import BladSkarbonki

KLUCZ_POWROTU = "0"


@dataclass
class OpcjaMenu:
    """Jedna pozycja menu: opis i funkcja do wywołania."""

    etykieta: str
    akcja: Callable[[], None]


class Menu:
    """Menu z numerowanymi opcjami.

    Podmenu to zwykła opcja, której akcją jest metoda uruchom() innego menu.
    """

    def __init__(self, tytul: str, opcje: list[OpcjaMenu], powrot: str = "Powrót") -> None:
        self.tytul = tytul
        self.powrot = powrot
        self.opcje = {str(numer): opcja for numer, opcja in enumerate(opcje, start=1)}

    def pokaz(self) -> None:
        """Wypisuje tytuł i wszystkie opcje."""
        print(f"\n--- {self.tytul} ---")
        for klucz, opcja in self.opcje.items():
            print(f"{klucz}. {opcja.etykieta}")
        print(f"{KLUCZ_POWROTU}. {self.powrot}")

    def uruchom(self) -> None:
        """Obsługuje wybory użytkownika aż do wyjścia z menu.

        Przewidziany błąd w opcji nie kończy programu, tylko wraca do menu.
        """
        dozwolone = (*self.opcje, KLUCZ_POWROTU)
        while True:
            self.pokaz()
            try:
                klucz = wczytaj_wybor("Wybór", dozwolone)
                if klucz == KLUCZ_POWROTU:
                    break
                self.opcje[klucz].akcja()
            except BladSkarbonki as blad:
                print(f"  ! {blad}")
