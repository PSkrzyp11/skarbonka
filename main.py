"""Punkt startowy aplikacji Skarbonka."""

import logging
import sys

from skarbonka.services.zestaw import utworz_serwisy
from skarbonka.ui import widoki
from skarbonka.ui.aplikacja import Aplikacja
from skarbonka.utils.logi import skonfiguruj_logi

logger = logging.getLogger("skarbonka.main")


def main() -> None:
    """Uruchamia aplikację i pilnuje spokojnego zakończenia programu.

    Znaki, których konsola nie potrafi wyświetlić, są zastępowane, dzięki
    czemu program działa także ze starszymi kodowaniami Windows.
    """
    sys.stdout.reconfigure(errors="replace")
    if not skonfiguruj_logi():
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
