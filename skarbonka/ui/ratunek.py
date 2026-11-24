"""Otwieranie bazy z ratunkiem, gdy jej plik jest uszkodzony."""

import logging
from pathlib import Path

from skarbonka.services.zestaw import utworz_serwisy
from skarbonka.storage.baza import Baza, odloz_uszkodzona
from skarbonka.ui import widoki
from skarbonka.ui.wejscie import potwierdz
from skarbonka.wyjatki import AnulowanoOperacje, BladPliku, UszkodzonaBaza

logger = logging.getLogger(__name__)


def otworz_baze(sciezka: Path) -> Baza:
    """Otwiera bazę, a uszkodzoną odkłada na bok i zastępuje nową.

    Uszkodzony plik nigdy nie jest kasowany.
    """
    try:
        return Baza(sciezka)
    except UszkodzonaBaza as blad:
        logger.error("%s", blad)
        widoki.blad(str(blad))
    odlozona = odloz_uszkodzona(sciezka)
    widoki.blad(f"Uszkodzony plik przeniesiono do {odlozona}. Tworzę nową bazę.")
    baza = Baza(sciezka)
    try:
        _zaproponuj_kopie(baza)
    except AnulowanoOperacje as blad:
        widoki.blad(str(blad))
    return baza


def _zaproponuj_kopie(baza: Baza) -> None:
    """Przywraca najnowszą poprawną kopię, jeśli użytkownik się zgodzi."""
    serwis = utworz_serwisy(baza).kopie
    kopie = serwis.lista()
    if not kopie:
        print("Nie ma kopii zapasowej do przywrócenia.")
        return
    if not potwierdz("Przywrócić najnowszą kopię zapasową?"):
        return
    for kopia in kopie:
        try:
            serwis.przywroc(kopia)
        except BladPliku as blad:
            widoki.blad(f"{blad} Próbuję starszej kopii.")
            continue
        widoki.sukces(f"Przywrócono kopię {kopia.name}.")
        break
    else:
        widoki.blad("Żadnej kopii nie udało się przywrócić.")
