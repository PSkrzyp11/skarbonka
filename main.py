"""Punkt startowy aplikacji Skarbonka."""

import argparse
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from skarbonka import __version__, demo
from skarbonka.config import PLIK_BAZY, PLIK_DEMO
from skarbonka.services.zestaw import Serwisy, dodaj_dane_startowe, utworz_serwisy
from skarbonka.storage.baza import Baza
from skarbonka.ui import widoki
from skarbonka.ui.aplikacja import Aplikacja
from skarbonka.ui.ratunek import otworz_baze
from skarbonka.ui.wejscie import potwierdz
from skarbonka.utils.logi import skonfiguruj_logi
from skarbonka.wyjatki import BladBazy, BladPliku, BrakBiblioteki

logger = logging.getLogger("skarbonka.main")


def wczytaj_argumenty(argumenty: list[str] | None = None) -> argparse.Namespace:
    """Odczytuje opcje podane przy uruchomieniu programu."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Skarbonka - menedżer budżetu domowego.",
        add_help=False,
    )
    parser.add_argument("-h", "--pomoc", action="help", help="pokaż tę pomoc i zakończ")
    parser.add_argument(
        "--wersja", action="version", version=f"Skarbonka {__version__}", help="pokaż wersję"
    )
    wybor_bazy = parser.add_mutually_exclusive_group()
    wybor_bazy.add_argument(
        "--baza", type=Path, default=PLIK_BAZY, metavar="PLIK", help="użyj innego pliku bazy"
    )
    wybor_bazy.add_argument(
        "--demo", action="store_true", help="użyj osobnej bazy z przykładowymi danymi"
    )
    parser.add_argument("--okno", action="store_true", help="uruchom w oknie zamiast w konsoli")
    parser.add_argument("--bez-kolorow", action="store_true", help="wyłącz kolory")
    parser.add_argument("--debug", action="store_true", help="zapisuj szczegółowe logi")
    return parser.parse_args(argumenty)


@dataclass
class Interfejs:
    """Sposób rozmowy z użytkownikiem: konsola albo okno."""

    pokaz: Callable[[str], None]
    zapytaj: Callable[[str], bool]
    uruchom: Callable[[Serwisy], None]


def wybierz_interfejs(czy_okno: bool) -> Interfejs:
    """Zwraca wybrany interfejs. Okno jest ładowane tylko wtedy, gdy jest potrzebne."""
    if not czy_okno:
        return Interfejs(widoki.blad, potwierdz, lambda serwisy: Aplikacja(serwisy).uruchom())
    try:
        from skarbonka.gui import komunikaty
        from skarbonka.gui.okno import uruchom_okno
    except ImportError as blad:
        raise BrakBiblioteki("Okno wymaga bibliotek tkinter i customtkinter.") from blad
    return Interfejs(komunikaty.pokaz, komunikaty.zapytaj, uruchom_okno)


def przygotuj_serwisy(baza: Baza, czy_demo: bool, pokaz: Callable[[str], None]) -> Serwisy:
    """Tworzy serwisy, dane startowe i kopię dzienną."""
    serwisy = utworz_serwisy(baza)
    dodaj_dane_startowe(serwisy)
    if czy_demo and not serwisy.transakcje.wszystkie():
        demo.wypelnij(baza, serwisy)
    try:
        serwisy.kopie.utworz_dzienna()
    except (BladPliku, OSError) as blad:
        logger.warning("Brak kopii automatycznej: %s", blad)
        pokaz(f"Nie udało się utworzyć kopii automatycznej: {blad}")
    return serwisy


def main(argumenty: list[str] | None = None) -> int:
    """Uruchamia aplikację i zwraca kod zakończenia: 0, a po awarii 1.

    Znaki, których konsola nie potrafi wyświetlić, są zastępowane, dzięki
    czemu program działa także ze starszymi kodowaniami Windows. Okno
    uruchomione ze skrótu nie ma żadnej konsoli.
    """
    for wyjscie in (sys.stdout, sys.stderr):
        if wyjscie is not None:
            wyjscie.reconfigure(errors="replace")
    opcje = wczytaj_argumenty(argumenty)
    if opcje.bez_kolorow:
        widoki.wylacz_kolory()
    sa_logi = skonfiguruj_logi(szczegolowe=opcje.debug)
    logger.info("Start aplikacji")
    baza = None
    kod = 0
    interfejs = None
    try:
        interfejs = wybierz_interfejs(opcje.okno)
        if not sa_logi:
            interfejs.pokaz("Nie można utworzyć pliku logów. Aplikacja działa bez logowania.")
        sciezka = PLIK_DEMO if opcje.demo else opcje.baza
        baza = otworz_baze(sciezka, interfejs.pokaz, interfejs.zapytaj)
        interfejs.uruchom(przygotuj_serwisy(baza, opcje.demo, interfejs.pokaz))
    except (KeyboardInterrupt, EOFError):
        print()
        print("Zakończono na życzenie użytkownika.")
    except (BladBazy, BrakBiblioteki) as blad:
        logger.error("%s", blad)
        _pokaz_awarie(interfejs, str(blad))
        kod = 1
    except Exception:
        logger.exception("Błąd, który zatrzymał aplikację")
        _pokaz_awarie(interfejs, "Wystąpił nieoczekiwany błąd. Szczegóły są w pliku logów.")
        kod = 1
    else:
        print("Do zobaczenia!")
    finally:
        if baza is not None:
            baza.zamknij()
        logger.info("Koniec pracy")
    return kod


def _pokaz_awarie(interfejs: Interfejs | None, tekst: str) -> None:
    """Pokazuje błąd w wybranym interfejsie, a gdy go nie ma, w konsoli."""
    pokaz = widoki.blad if interfejs is None else interfejs.pokaz
    pokaz(tekst)


if __name__ == "__main__":
    sys.exit(main())
