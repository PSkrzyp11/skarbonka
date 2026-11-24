"""Zapisywanie zdarzeń i błędów do pliku."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from skarbonka.config import PLIK_LOGU

FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
MAKS_ROZMIAR = 200_000
LICZBA_STARYCH_PLIKOW = 3


def skonfiguruj_logi(plik: Path = PLIK_LOGU, szczegolowe: bool = False) -> bool:
    """Włącza zapis logów do pliku.

    Zwraca False, gdy pliku nie da się utworzyć. Aplikacja działa wtedy
    dalej, tylko bez logów.
    """
    logger = logging.getLogger("skarbonka")
    logger.setLevel(logging.DEBUG if szczegolowe else logging.INFO)
    try:
        plik.parent.mkdir(parents=True, exist_ok=True)
        wyjscie = RotatingFileHandler(
            plik, maxBytes=MAKS_ROZMIAR, backupCount=LICZBA_STARYCH_PLIKOW, encoding="utf-8"
        )
    except OSError:
        logger.addHandler(logging.NullHandler())
        return False
    else:
        wyjscie.setFormatter(logging.Formatter(FORMAT))
        logger.addHandler(wyjscie)
        return True
