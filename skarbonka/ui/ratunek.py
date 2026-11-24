"""Otwieranie bazy z ratunkiem, gdy jej plik jest uszkodzony.

Sposób pokazania komunikatu i zadania pytania jest parametrem, dlatego z tego
samego kodu korzysta konsola i okno.
"""

import logging
from collections.abc import Callable
from pathlib import Path

from skarbonka.services.zestaw import utworz_serwisy
from skarbonka.storage.baza import Baza, odloz_uszkodzona
from skarbonka.ui import widoki
from skarbonka.ui.wejscie import potwierdz
from skarbonka.wyjatki import AnulowanoOperacje, BladPliku, UszkodzonaBaza

logger = logging.getLogger(__name__)

Pokaz = Callable[[str], None]
Zapytaj = Callable[[str], bool]


def otworz_baze(sciezka: Path, pokaz: Pokaz = widoki.blad, zapytaj: Zapytaj = potwierdz) -> Baza:
    """Otwiera bazę, a uszkodzoną odkłada na bok i zastępuje nową.

    Uszkodzony plik nigdy nie jest kasowany.
    """
    try:
        return Baza(sciezka)
    except UszkodzonaBaza as blad:
        logger.error("%s", blad)
        komunikat = str(blad)
    odlozona = odloz_uszkodzona(sciezka)
    pokaz(f"{komunikat} Plik przeniesiono do {odlozona}. Tworzę nową bazę.")
    baza = Baza(sciezka)
    try:
        _zaproponuj_kopie(baza, pokaz, zapytaj)
    except AnulowanoOperacje as blad:
        pokaz(str(blad))
    return baza


def _zaproponuj_kopie(baza: Baza, pokaz: Pokaz, zapytaj: Zapytaj) -> None:
    """Przywraca najnowszą poprawną kopię, jeśli użytkownik się zgodzi."""
    serwis = utworz_serwisy(baza).kopie
    kopie = serwis.lista()
    if not kopie:
        pokaz("Nie ma kopii zapasowej do przywrócenia.")
        return
    if not zapytaj("Przywrócić najnowszą kopię zapasową?"):
        return
    for kopia in kopie:
        try:
            serwis.przywroc(kopia)
        except BladPliku as blad:
            pokaz(f"{blad} Próbuję starszej kopii.")
            continue
        pokaz(f"Przywrócono kopię {kopia.name}.")
        break
    else:
        pokaz("Żadnej kopii nie udało się przywrócić.")
