"""Kopie zapasowe całej bazy w plikach JSON."""

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

from skarbonka.storage.baza import TABELE, Baza
from skarbonka.storage.pliki_json import wczytaj_json, zapisz_json
from skarbonka.storage.repozytoria import Repozytorium
from skarbonka.wyjatki import BladBazy, UszkodzonyPlik

logger = logging.getLogger(__name__)

WERSJA_KOPII = 1
ILE_AUTOMATYCZNYCH = 7


class SerwisKopii:
    """Tworzenie i przywracanie kopii zapasowych."""

    def __init__(self, baza: Baza, repozytoria: list[Repozytorium]) -> None:
        self._baza = baza
        self._repozytoria = repozytoria
        plik_bazy = Path(baza.sciezka)
        self._katalog = plik_bazy.parent / "kopie"
        self._przedrostek = f"{plik_bazy.stem}-"

    def lista(self) -> list[Path]:
        """Zwraca kopie tej bazy, od najnowszej."""
        if not self._katalog.is_dir():
            return []
        kopie = [
            plik
            for plik in self._katalog.glob("*.json")
            if plik.name.startswith(self._przedrostek)
        ]
        return sorted(kopie, key=lambda plik: plik.stat().st_mtime, reverse=True)

    def utworz(self, nazwa: str | None = None) -> Path:
        """Zapisuje wszystkie tabele do pliku i zwraca jego ścieżkę."""
        nazwa = nazwa or f"{datetime.now():%Y%m%d-%H%M%S}"
        sciezka = self._katalog / self._nazwa_pliku(nazwa)
        zapisz_json(sciezka, self._zawartosc())
        logger.info("Utworzono kopię %s", sciezka.name)
        return sciezka

    def utworz_dzienna(self) -> Path | None:
        """Raz dziennie zapisuje kopię automatyczną i usuwa najstarsze."""
        nazwa = f"auto-{date.today():%Y%m%d}"
        if not self._sa_transakcje() or (self._katalog / self._nazwa_pliku(nazwa)).exists():
            return None
        sciezka = self.utworz(nazwa)
        poczatek = f"{self._przedrostek}auto-"
        automatyczne = [plik for plik in self.lista() if plik.name.startswith(poczatek)]
        for stara in sorted(automatyczne, reverse=True)[ILE_AUTOMATYCZNYCH:]:
            stara.unlink(missing_ok=True)
        return sciezka

    def policz(self, sciezka: Path) -> dict[str, int]:
        """Zwraca liczbę rekordów w każdej tabeli kopii."""
        return {nazwa: len(wiersze) for nazwa, wiersze in self._wczytaj(sciezka).items()}

    def przywroc(self, sciezka: Path) -> None:
        """Zastępuje dane zawartością kopii. Błąd w kopii zostawia dane bez zmian."""
        tabele = self._wczytaj(sciezka)
        if self._sa_transakcje():
            self.utworz(f"przed-przywroceniem-{datetime.now():%Y%m%d-%H%M%S}")
        try:
            with self._baza.transakcja():
                self._zastap(tabele)
        except BladBazy as blad:
            raise UszkodzonyPlik(f"Kopia {sciezka.name} zawiera błędne dane. {blad}") from blad
        logger.info("Przywrócono kopię %s", sciezka.name)

    def _zastap(self, tabele: dict[str, list[dict[str, Any]]]) -> None:
        """Czyści tabele, wstawia nowe wiersze i próbuje wczytać każdy obiekt."""
        for tabela in reversed(TABELE):
            self._baza.wykonaj(f"DELETE FROM {tabela}")
        for tabela in TABELE:
            for wiersz in tabele.get(tabela, []):
                self._baza.wstaw(tabela, wiersz)
        for repozytorium in self._repozytoria:
            repozytorium.wszystkie()

    def _wczytaj(self, sciezka: Path) -> dict[str, list[dict[str, Any]]]:
        """Czyta kopię i sprawdza jej budowę."""
        dane = wczytaj_json(sciezka)
        if not isinstance(dane, dict) or dane.get("wersja") != WERSJA_KOPII:
            raise UszkodzonyPlik(f"Plik {sciezka.name} nie jest kopią zapasową Skarbonki.")
        tabele = dane.get("tabele")
        if not isinstance(tabele, dict) or not set(tabele) <= set(TABELE):
            raise UszkodzonyPlik(f"Plik {sciezka.name} ma nieznane tabele.")
        for nazwa, wiersze in tabele.items():
            kolumny = self._baza.kolumny(nazwa)
            if not isinstance(wiersze, list) or not all(
                isinstance(wiersz, dict) and "id" in wiersz and set(wiersz) <= kolumny
                for wiersz in wiersze
            ):
                raise UszkodzonyPlik(f"Plik {sciezka.name} ma błędną tabelę {nazwa}.")
        return tabele

    def _nazwa_pliku(self, nazwa: str) -> str:
        """Zwraca nazwę pliku kopii tej bazy."""
        return f"{self._przedrostek}{nazwa}.json"

    def _sa_transakcje(self) -> bool:
        """Informuje, czy w bazie jest choć jedna transakcja."""
        return bool(self._baza.zapytaj("SELECT id FROM transakcje LIMIT 1"))

    def _zawartosc(self) -> dict[str, Any]:
        """Zwraca wszystkie tabele jako słowniki."""
        return {
            "wersja": WERSJA_KOPII,
            "utworzono": datetime.now().isoformat(timespec="seconds"),
            "tabele": {
                tabela: [dict(w) for w in self._baza.zapytaj(f"SELECT * FROM {tabela} ORDER BY id")]
                for tabela in TABELE
            },
        }
