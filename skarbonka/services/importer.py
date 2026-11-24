"""Import transakcji z wyciągu bankowego w CSV."""

import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from skarbonka.config import MAKS_DLUGOSC_OPISU
from skarbonka.models.importy import ProfilCSV
from skarbonka.models.transakcja import Przelew, Przychod, Transakcja, Wydatek
from skarbonka.services.kategorie import SerwisKategorii
from skarbonka.storage.baza import Baza
from skarbonka.storage.pliki_csv import czytaj_wiersze
from skarbonka.storage.repozytoria import RepozytoriumTransakcji
from skarbonka.utils.walidacja import parsuj_date, parsuj_kwote
from skarbonka.wyjatki import BladWalidacji, NieprawidlowaKwota

logger = logging.getLogger(__name__)

DLUGOSC_DATY = 10


@dataclass
class PodgladImportu:
    """Wynik wczytania pliku, zanim cokolwiek trafi do bazy."""

    plik: str
    nowe: list[Transakcja] = field(default_factory=list)
    bledy: list[str] = field(default_factory=list)


class Importer:
    """Zamienia wiersze pliku CSV na transakcje."""

    def __init__(
        self, baza: Baza, transakcje: RepozytoriumTransakcji, kategorie: SerwisKategorii
    ) -> None:
        self._baza = baza
        self._transakcje = transakcje
        self._kategorie = kategorie

    def przygotuj(self, sciezka: Path, profil: ProfilCSV, konto_id: int) -> PodgladImportu:
        """Wczytuje plik i oddziela poprawne wiersze od błędnych."""
        podglad = PodgladImportu(sciezka.name)
        wszystkich = 0
        for numer, wiersz in czytaj_wiersze(sciezka, profil):
            try:
                transakcja = self._utworz(wiersz, profil, konto_id)
            except BladWalidacji as blad:
                podglad.bledy.append(f"Linia {numer}: {blad}")
            else:
                podglad.nowe.append(transakcja)
            finally:
                wszystkich += 1
        logger.info("Plik %s: %s wierszy, %s błędnych", sciezka, wszystkich, len(podglad.bledy))
        return podglad

    def zapisz(self, transakcje: list[Transakcja]) -> int:
        """Zapisuje wszystkie transakcje albo żadnej i zwraca ich liczbę."""
        with self._baza.transakcja():
            for transakcja in transakcje:
                self._transakcje.dodaj(transakcja)
        logger.info("Zaimportowano %s transakcji", len(transakcje))
        return len(transakcje)

    def _utworz(self, wiersz: dict[str, str], profil: ProfilCSV, konto_id: int) -> Transakcja:
        """Tworzy transakcję z jednego wiersza pliku."""

        def komorka(kolumna: str) -> str:
            return wiersz.get(kolumna.casefold(), "")

        if komorka(profil.kolumna_rodzaj).casefold() == Przelew.RODZAJ:
            raise BladWalidacji("przelew między własnymi kontami, pominięto.")
        kwota = parsuj_kwote(komorka(profil.kolumna_kwota), minimum=None)
        if kwota == 0:
            raise NieprawidlowaKwota("Kwota jest równa zero.")
        data = parsuj_date(komorka(profil.kolumna_data)[:DLUGOSC_DATY], najpozniej=date.today())
        klasa = Wydatek if kwota < 0 else Przychod
        kategoria_id = self._kategoria_id(klasa, komorka(profil.kolumna_kategoria))
        opis = self._oczysc(komorka(profil.kolumna_opis))
        return klasa(data, abs(kwota), opis, konto_id, kategoria_id)

    def _kategoria_id(self, klasa: type[Transakcja], nazwa: str) -> int:
        """Zwraca numer kategorii o podanej nazwie, a gdy jej brak – domyślnej."""
        pasujace = {k.nazwa.casefold(): k for k in self._kategorie.pasujace(klasa)}
        kategoria = pasujace.get(nazwa.casefold()) or self._kategorie.domyslna(klasa)
        return kategoria.id

    @staticmethod
    def _oczysc(opis: str) -> str:
        """Usuwa z opisu zbędne znaki i skraca go do dozwolonej długości."""
        widoczne = "".join(znak if znak.isprintable() else " " for znak in opis)
        return " ".join(widoczne.split())[:MAKS_DLUGOSC_OPISU] or "Import"
