"""Import transakcji z wyciągu bankowego w CSV."""

import logging
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from pathlib import Path

from skarbonka.config import MAKS_DLUGOSC_OPISU
from skarbonka.models.importy import Import, ProfilCSV
from skarbonka.models.kategoria import Kategoria
from skarbonka.models.transakcja import Przelew, Przychod, Transakcja, Wydatek
from skarbonka.services.kategorie import SerwisKategorii
from skarbonka.services.kategoryzacja import Kategoryzator
from skarbonka.storage.baza import Baza
from skarbonka.storage.pliki_csv import czytaj_wiersze
from skarbonka.storage.repozytoria import RepozytoriumImportow, RepozytoriumTransakcji
from skarbonka.utils.walidacja import parsuj_date, parsuj_kwote
from skarbonka.wyjatki import BladWalidacji, NieprawidlowaKwota, NieZnalezionoRekordu

logger = logging.getLogger(__name__)

DLUGOSC_DATY = 10


@dataclass
class PodgladImportu:
    """Wynik wczytania pliku, zanim cokolwiek trafi do bazy."""

    plik: str
    nowe: list[Transakcja] = field(default_factory=list)
    duplikaty: list[Transakcja] = field(default_factory=list)
    bledy: list[str] = field(default_factory=list)


class Importer:
    """Zamienia wiersze pliku CSV na transakcje."""

    def __init__(
        self,
        baza: Baza,
        transakcje: RepozytoriumTransakcji,
        importy: RepozytoriumImportow,
        kategorie: SerwisKategorii,
        kategoryzator: Kategoryzator,
    ) -> None:
        self._baza = baza
        self._transakcje = transakcje
        self._importy = importy
        self._kategorie = kategorie
        self._kategoryzator = kategoryzator

    def przygotuj(self, sciezka: Path, profil: ProfilCSV, konto_id: int) -> PodgladImportu:
        """Wczytuje plik i dzieli wiersze na nowe, duplikaty i błędne.

        Duplikat to operacja, która jest już w bazie. Dwie identyczne operacje
        w jednym pliku są dozwolone, bo tak bywa na prawdziwych wyciągach.
        """
        podglad = PodgladImportu(sciezka.name)
        znane = {t.odcisk for t in self._transakcje.wszystkie()}
        wszystkich = 0
        for numer, wiersz in czytaj_wiersze(sciezka, profil):
            try:
                transakcja = self._utworz(wiersz, profil, konto_id)
            except BladWalidacji as blad:
                podglad.bledy.append(f"Linia {numer}: {blad}")
            else:
                lista = podglad.duplikaty if transakcja.odcisk in znane else podglad.nowe
                lista.append(transakcja)
            finally:
                wszystkich += 1
        logger.info("Plik %s: %s wierszy, %s błędnych", sciezka, wszystkich, len(podglad.bledy))
        return podglad

    def zapisz(self, plik: str, transakcje: list[Transakcja]) -> Import:
        """Zapisuje wszystkie transakcje albo żadnej."""
        with self._baza.transakcja():
            wykonany = self._importy.dodaj(Import(plik, datetime.now()))
            for transakcja in transakcje:
                self._transakcje.dodaj(replace(transakcja, import_id=wykonany.id))
        logger.info("Import nr %s: %s transakcji", wykonany.id, len(transakcje))
        return wykonany

    def ostatni(self) -> Import:
        """Zwraca ostatnio wykonany import."""
        importy = self._importy.wszystkie()
        if not importy:
            raise NieZnalezionoRekordu("Nie ma importu do cofnięcia.")
        return max(importy, key=lambda i: i.id)

    def cofnij(self, wykonany: Import) -> int:
        """Usuwa transakcje z importu i zwraca ich liczbę."""
        with self._baza.transakcja():
            liczba = self._transakcje.usun_z_importu(wykonany.id)
            self._importy.usun(wykonany.id)
        logger.info("Cofnięto import nr %s: %s transakcji", wykonany.id, liczba)
        return liczba

    def _utworz(self, wiersz: dict[str, str], profil: ProfilCSV, konto_id: int) -> Transakcja:
        """Tworzy transakcję z jednego wiersza pliku."""

        def komorka(kolumna: str) -> str:
            return wiersz.get(kolumna.casefold(), "") if kolumna else ""

        if komorka(profil.kolumna_rodzaj).casefold() == Przelew.RODZAJ:
            raise BladWalidacji("przelew między własnymi kontami, pominięto.")
        kwota = parsuj_kwote(komorka(profil.kolumna_kwota), minimum=None)
        if kwota == 0:
            raise NieprawidlowaKwota("Kwota jest równa zero.")
        data = parsuj_date(komorka(profil.kolumna_data)[:DLUGOSC_DATY], najpozniej=date.today())
        klasa = Wydatek if kwota < 0 else Przychod
        opis = self._oczysc(komorka(profil.kolumna_opis))
        kategoria = self._kategoria(klasa, komorka(profil.kolumna_kategoria), opis)
        return klasa(data, abs(kwota), opis, konto_id, kategoria.id)

    def _kategoria(self, klasa: type[Transakcja], nazwa: str, opis: str) -> Kategoria:
        """Wybiera kategorię: najpierw z pliku, potem z reguł, na końcu domyślną."""
        pasujace = {k.nazwa.casefold(): k for k in self._kategorie.pasujace(klasa)}
        return (
            pasujace.get(nazwa.casefold())
            or self._kategoryzator.dopasuj(opis, klasa)
            or self._kategorie.domyslna(klasa)
        )

    @staticmethod
    def _oczysc(opis: str) -> str:
        """Usuwa z opisu zbędne znaki i skraca go do dozwolonej długości."""
        widoczne = "".join(znak if znak.isprintable() else " " for znak in opis)
        return " ".join(widoczne.split())[:MAKS_DLUGOSC_OPISU] or "Import"
