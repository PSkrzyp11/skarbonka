"""Składa wszystkie serwisy w jeden zestaw dla interfejsu."""

from dataclasses import dataclass

from skarbonka.config import KATEGORIE_PRZYCHODOW, KATEGORIE_WYDATKOW
from skarbonka.models.enums import TypKonta
from skarbonka.services.kategorie import SerwisKategorii
from skarbonka.services.konta import SerwisKont
from skarbonka.services.transakcje import SerwisTransakcji
from skarbonka.storage.repozytoria import Repozytorium


@dataclass
class Serwisy:
    """Wszystkie serwisy, z których korzystają ekrany."""

    transakcje: SerwisTransakcji
    konta: SerwisKont
    kategorie: SerwisKategorii


def utworz_serwisy() -> Serwisy:
    """Tworzy serwisy na wspólnych repozytoriach i uzupełnia dane startowe."""
    transakcje = Repozytorium()
    serwisy = Serwisy(
        transakcje=SerwisTransakcji(transakcje),
        konta=SerwisKont(Repozytorium(), transakcje),
        kategorie=SerwisKategorii(Repozytorium(), transakcje),
    )
    _dodaj_dane_startowe(serwisy)
    return serwisy


def _dodaj_dane_startowe(serwisy: Serwisy) -> None:
    """Dodaje konto i kategorie, jeśli jeszcze ich nie ma."""
    if not serwisy.konta.wszystkie():
        serwisy.konta.dodaj("Portfel", TypKonta.GOTOWKA)
    if not serwisy.kategorie.wszystkie():
        for nazwa in KATEGORIE_WYDATKOW:
            serwisy.kategorie.dodaj(nazwa)
        for nazwa in KATEGORIE_PRZYCHODOW:
            serwisy.kategorie.dodaj(nazwa, czy_wydatek=False)
