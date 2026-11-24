"""Punkt startowy aplikacji Skarbonka."""

import argparse
import logging
import sys

from skarbonka import __version__
from skarbonka.services.zestaw import utworz_serwisy
from skarbonka.ui import widoki
from skarbonka.ui.aplikacja import Aplikacja
from skarbonka.utils.logi import skonfiguruj_logi

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
    parser.add_argument("--bez-kolorow", action="store_true", help="wyłącz kolory")
    parser.add_argument("--debug", action="store_true", help="zapisuj szczegółowe logi")
    return parser.parse_args(argumenty)


def main(argumenty: list[str] | None = None) -> None:
    """Uruchamia aplikację i pilnuje spokojnego zakończenia programu.

    Znaki, których konsola nie potrafi wyświetlić, są zastępowane, dzięki
    czemu program działa także ze starszymi kodowaniami Windows.
    """
    for wyjscie in (sys.stdout, sys.stderr):
        wyjscie.reconfigure(errors="replace")
    opcje = wczytaj_argumenty(argumenty)
    if opcje.bez_kolorow:
        widoki.wylacz_kolory()
    if not skonfiguruj_logi(szczegolowe=opcje.debug):
        widoki.blad("Nie można utworzyć pliku logów. Aplikacja działa bez logowania.")
    logger.info("Start aplikacji")
    try:
        Aplikacja(utworz_serwisy()).uruchom()
    except (KeyboardInterrupt, EOFError):
        print()
        print("Zakończono na życzenie użytkownika.")
    except Exception:
        logger.exception("Błąd, który zatrzymał aplikację")
        widoki.blad("Wystąpił nieoczekiwany błąd. Szczegóły są w pliku logów.")
    else:
        print("Do zobaczenia!")
    finally:
        logger.info("Koniec pracy")


if __name__ == "__main__":
    main()
