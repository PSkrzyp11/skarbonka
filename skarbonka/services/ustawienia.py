"""Ustawienia użytkownika zapisane w pliku JSON."""

import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from skarbonka.storage.pliki_json import wczytaj_json, zapisz_json
from skarbonka.wyjatki import BladPliku

logger = logging.getLogger(__name__)


MOTYWY = ("jasny", "ciemny")


@dataclass
class Ustawienia:
    """Wartości, które użytkownik może zmienić."""

    prog_ostrzezen: int = 80
    motyw: str = MOTYWY[0]

    def __post_init__(self) -> None:
        if not isinstance(self.prog_ostrzezen, int) or not 1 <= self.prog_ostrzezen <= 100:
            raise ValueError("Próg ostrzeżeń musi być liczbą od 1 do 100.")
        if self.motyw not in MOTYWY:
            raise ValueError(f"Dostępne motywy: {', '.join(MOTYWY)}.")


class SerwisUstawien:
    """Odczyt i zapis ustawień."""

    def __init__(self, plik: Path) -> None:
        self._plik = plik

    def wczytaj(self) -> Ustawienia:
        """Zwraca zapisane ustawienia, a gdy pliku brak lub jest zły – domyślne."""
        if not self._plik.exists():
            return Ustawienia()
        try:
            return Ustawienia(**wczytaj_json(self._plik))
        except (BladPliku, TypeError, ValueError) as blad:
            logger.warning("Błędne ustawienia, używam domyślnych: %s", blad)
            return Ustawienia()

    def zapisz(self, ustawienia: Ustawienia) -> None:
        """Zapisuje ustawienia do pliku."""
        zapisz_json(self._plik, asdict(ustawienia))
