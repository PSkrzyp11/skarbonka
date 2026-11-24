"""Uniwersalne menu tekstowe i klasa bazowa ekranów."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

from skarbonka.services.zestaw import Serwisy
from skarbonka.ui import widoki
from skarbonka.ui.wejscie import wczytaj_wybor
from skarbonka.wyjatki import AnulowanoOperacje, BladSkarbonki

logger = logging.getLogger(__name__)

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
        pozycje = {klucz: opcja.etykieta for klucz, opcja in self.opcje.items()}
        pozycje[KLUCZ_POWROTU] = self.powrot
        widoki.pokaz_menu(self.tytul, pozycje)

    def uruchom(self) -> None:
        """Obsługuje wybory użytkownika aż do wyjścia z menu.

        Błąd w opcji nie kończy programu, tylko wraca do menu. Wyjątkiem jest
        koniec danych wejściowych, po którym nie ma już czego wczytywać.
        """
        dozwolone = (*self.opcje, KLUCZ_POWROTU)
        while True:
            self.pokaz()
            try:
                klucz = wczytaj_wybor("Wybór", dozwolone)
                if klucz == KLUCZ_POWROTU:
                    break
                self.opcje[klucz].akcja()
            except AnulowanoOperacje as blad:
                widoki.blad(str(blad))
            except BladSkarbonki as blad:
                logger.warning("%s: %s", type(blad).__name__, blad)
                widoki.blad(str(blad))
            except EOFError:
                raise
            except Exception:
                logger.exception("Nieoczekiwany błąd w menu %s", self.tytul)
                widoki.blad("Nieoczekiwany błąd. Szczegóły są w pliku logów.")


class Ekran(ABC):
    """Wspólna część ekranów: dostęp do serwisów i własne menu."""

    TYTUL = ""

    def __init__(self, serwisy: Serwisy) -> None:
        self.serwisy = serwisy

    @abstractmethod
    def opcje(self) -> list[OpcjaMenu]:
        """Zwraca pozycje menu ekranu."""

    def uruchom(self) -> None:
        """Pokazuje menu ekranu."""
        Menu(self.TYTUL, self.opcje()).uruchom()
