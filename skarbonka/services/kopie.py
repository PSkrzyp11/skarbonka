"""Kopie zapasowe całej bazy w plikach JSON."""

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

from skarbonka.storage.baza import TABELE, Baza
from skarbonka.storage.pliki_json import zapisz_json

logger = logging.getLogger(__name__)

WERSJA_KOPII = 1
ILE_AUTOMATYCZNYCH = 7


class SerwisKopii:
    """Tworzenie kopii zapasowych."""

    def __init__(self, baza: Baza) -> None:
        self._baza = baza
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
        automatyczne = sorted(self._katalog.glob(self._nazwa_pliku("auto-*")), reverse=True)
        for stara in automatyczne[ILE_AUTOMATYCZNYCH:]:
            stara.unlink(missing_ok=True)
        return sciezka

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
