"""Składa wszystkie serwisy w jeden zestaw dla interfejsu."""

from dataclasses import dataclass

from skarbonka.config import KATEGORIE_PRZYCHODOW, KATEGORIE_WYDATKOW
from skarbonka.models.enums import TypKonta
from skarbonka.services.eksport import Eksporter
from skarbonka.services.kategorie import SerwisKategorii
from skarbonka.services.konta import SerwisKont
from skarbonka.services.transakcje import SerwisTransakcji
from skarbonka.storage.baza import Baza
from skarbonka.storage.repozytoria import (
    RepozytoriumKategorii,
    RepozytoriumKont,
    RepozytoriumTransakcji,
)


@dataclass
class Serwisy:
    """Wszystkie serwisy, z których korzystają ekrany."""

    transakcje: SerwisTransakcji
    konta: SerwisKont
    kategorie: SerwisKategorii
    eksporter: Eksporter


def utworz_serwisy(baza: Baza) -> Serwisy:
    """Tworzy serwisy korzystające ze wspólnej bazy."""
    transakcje = RepozytoriumTransakcji(baza)
    konta = SerwisKont(RepozytoriumKont(baza), transakcje)
    kategorie = SerwisKategorii(RepozytoriumKategorii(baza), transakcje)
    return Serwisy(
        transakcje=SerwisTransakcji(transakcje),
        konta=konta,
        kategorie=kategorie,
        eksporter=Eksporter(konta, kategorie),
    )


def dodaj_dane_startowe(serwisy: Serwisy) -> None:
    """Dodaje konto i kategorie, jeśli jeszcze ich nie ma."""
    if not serwisy.konta.wszystkie():
        serwisy.konta.dodaj("Portfel", TypKonta.GOTOWKA)
    if not serwisy.kategorie.wszystkie():
        for nazwa in KATEGORIE_WYDATKOW:
            serwisy.kategorie.dodaj(nazwa)
        for nazwa in KATEGORIE_PRZYCHODOW:
            serwisy.kategorie.dodaj(nazwa, czy_wydatek=False)
