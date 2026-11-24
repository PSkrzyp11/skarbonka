"""Składa wszystkie serwisy w jeden zestaw dla interfejsu."""

from dataclasses import dataclass
from pathlib import Path

from skarbonka.config import KATEGORIE_PRZYCHODOW, KATEGORIE_WYDATKOW
from skarbonka.models.enums import TypKonta
from skarbonka.services.cykliczne import SerwisCyklicznych
from skarbonka.services.eksport import Eksporter
from skarbonka.services.importer import Importer
from skarbonka.services.kategorie import SerwisKategorii
from skarbonka.services.kategoryzacja import Kategoryzator
from skarbonka.services.konta import SerwisKont
from skarbonka.services.kopie import SerwisKopii
from skarbonka.services.planowanie import SerwisBudzetow, SerwisCeli
from skarbonka.services.profile import SerwisProfili
from skarbonka.services.prognoza import SerwisPrognozy
from skarbonka.services.raporty import SerwisRaportow
from skarbonka.services.transakcje import SerwisTransakcji
from skarbonka.services.ustawienia import SerwisUstawien
from skarbonka.services.waluty import SerwisWalut
from skarbonka.storage.baza import Baza
from skarbonka.storage.repozytoria import (
    RepozytoriumImportow,
    RepozytoriumKategorii,
    RepozytoriumKont,
    RepozytoriumTransakcji,
)
from skarbonka.storage.repozytoria_planu import (
    RepozytoriumBudzetow,
    RepozytoriumCeli,
    RepozytoriumCyklicznych,
    RepozytoriumKursow,
    RepozytoriumRegul,
    RepozytoriumWplat,
)


@dataclass
class Serwisy:
    """Wszystkie serwisy, z których korzystają ekrany."""

    katalog: Path
    transakcje: SerwisTransakcji
    konta: SerwisKont
    kategorie: SerwisKategorii
    kategoryzator: Kategoryzator
    budzety: SerwisBudzetow
    cele: SerwisCeli
    cykliczne: SerwisCyklicznych
    prognoza: SerwisPrognozy
    waluty: SerwisWalut
    eksporter: Eksporter
    importer: Importer
    kopie: SerwisKopii
    profile: SerwisProfili
    raporty: SerwisRaportow
    ustawienia: SerwisUstawien


def utworz_serwisy(baza: Baza, katalog: Path | None = None) -> Serwisy:
    """Tworzy serwisy korzystające ze wspólnej bazy.

    Pliki pomocnicze leżą w podanym katalogu, domyślnie obok bazy.
    """
    katalog = katalog or Path(baza.sciezka).parent

    repo_transakcji = RepozytoriumTransakcji(baza)
    repo_kont = RepozytoriumKont(baza)
    repo_kategorii = RepozytoriumKategorii(baza)
    repo_importow = RepozytoriumImportow(baza)
    repo_budzetow = RepozytoriumBudzetow(baza)
    repo_celi = RepozytoriumCeli(baza)
    repo_wplat = RepozytoriumWplat(baza)
    repo_cyklicznych = RepozytoriumCyklicznych(baza)
    repo_regul = RepozytoriumRegul(baza)
    repo_kursow = RepozytoriumKursow(baza)
    repozytoria = [
        repo_transakcji,
        repo_kont,
        repo_kategorii,
        repo_importow,
        repo_budzetow,
        repo_celi,
        repo_wplat,
        repo_cyklicznych,
        repo_regul,
        repo_kursow,
    ]

    ustawienia = SerwisUstawien(katalog / "ustawienia.json")
    transakcje = SerwisTransakcji(repo_transakcji)
    konta = SerwisKont(repo_kont, repo_transakcji)
    kategorie = SerwisKategorii(repo_kategorii, repo_transakcji)
    cykliczne = SerwisCyklicznych(baza, repo_cyklicznych, transakcje)
    kategoryzator = Kategoryzator(baza, repo_regul, kategorie, transakcje)
    budzety = SerwisBudzetow(repo_budzetow, transakcje, kategorie, ustawienia)
    cele = SerwisCeli(repo_celi, repo_wplat)
    return Serwisy(
        katalog=katalog,
        transakcje=transakcje,
        konta=konta,
        kategorie=kategorie,
        kategoryzator=kategoryzator,
        budzety=budzety,
        cele=cele,
        cykliczne=cykliczne,
        prognoza=SerwisPrognozy(transakcje, konta, cykliczne),
        waluty=SerwisWalut(repo_kursow),
        eksporter=Eksporter(konta, kategorie),
        importer=Importer(baza, repo_transakcji, repo_importow, kategorie, kategoryzator),
        kopie=SerwisKopii(baza, repozytoria),
        profile=SerwisProfili(katalog / "profile_csv.json"),
        raporty=SerwisRaportow(transakcje, konta, kategorie, budzety, cele),
        ustawienia=ustawienia,
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
