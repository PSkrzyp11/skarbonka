"""Składa wszystkie serwisy w jeden zestaw dla interfejsu."""

from dataclasses import dataclass
from pathlib import Path

from skarbonka.config import KATEGORIE_PRZYCHODOW, KATEGORIE_WYDATKOW, PLIK_PROFILI
from skarbonka.models.enums import TypKonta
from skarbonka.services.eksport import Eksporter
from skarbonka.services.importer import Importer
from skarbonka.services.kategorie import SerwisKategorii
from skarbonka.services.konta import SerwisKont
from skarbonka.services.kopie import SerwisKopii
from skarbonka.services.profile import SerwisProfili
from skarbonka.services.transakcje import SerwisTransakcji
from skarbonka.storage.baza import Baza
from skarbonka.storage.repozytoria import (
    RepozytoriumImportow,
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
    importer: Importer
    profile: SerwisProfili
    kopie: SerwisKopii


def utworz_serwisy(baza: Baza, plik_profili: Path = PLIK_PROFILI) -> Serwisy:
    """Tworzy serwisy korzystające ze wspólnej bazy."""
    repo_transakcji = RepozytoriumTransakcji(baza)
    repo_kont = RepozytoriumKont(baza)
    repo_kategorii = RepozytoriumKategorii(baza)
    repo_importow = RepozytoriumImportow(baza)
    konta = SerwisKont(repo_kont, repo_transakcji)
    kategorie = SerwisKategorii(repo_kategorii, repo_transakcji)
    return Serwisy(
        transakcje=SerwisTransakcji(repo_transakcji),
        konta=konta,
        kategorie=kategorie,
        eksporter=Eksporter(konta, kategorie),
        importer=Importer(baza, repo_transakcji, repo_importow, kategorie),
        profile=SerwisProfili(plik_profili),
        kopie=SerwisKopii(
            baza, [repo_kont, repo_kategorii, repo_importow, repo_transakcji]
        ),
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
