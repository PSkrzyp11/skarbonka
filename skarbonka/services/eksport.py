"""Eksport transakcji do pliku CSV."""

import logging
from pathlib import Path

from skarbonka.models.transakcja import Przelew, Transakcja
from skarbonka.services.kategorie import SerwisKategorii
from skarbonka.services.konta import SerwisKont
from skarbonka.storage.pliki_csv import zapisz_csv

logger = logging.getLogger(__name__)

NAGLOWKI = ["data", "rodzaj", "kwota", "opis", "konto", "konto docelowe", "kategoria"]


class Eksporter:
    """Zamienia transakcje na wiersze tabeli."""

    def __init__(self, konta: SerwisKont, kategorie: SerwisKategorii) -> None:
        self._konta = konta
        self._kategorie = kategorie

    def zapisz(self, transakcje: list[Transakcja], sciezka: Path) -> None:
        """Zapisuje transakcje do pliku CSV."""
        konta = self._konta.nazwy()
        kategorie = self._kategorie.nazwy()
        wiersze = [self._wiersz(t, konta, kategorie) for t in transakcje]
        zapisz_csv(sciezka, NAGLOWKI, wiersze)
        logger.info("Wyeksportowane transakcje: %s", len(wiersze))

    @staticmethod
    def _wiersz(
        transakcja: Transakcja, konta: dict[int, str], kategorie: dict[int, str]
    ) -> list[str]:
        """Zwraca komórki jednego wiersza. Wydatki mają kwotę ze znakiem minus."""
        znak = "-" if transakcja.wplyw < 0 else ""
        czy_przelew = isinstance(transakcja, Przelew)
        return [
            transakcja.data.isoformat(),
            transakcja.RODZAJ,
            znak + f"{transakcja.kwota:.2f}".replace(".", ","),
            transakcja.opis,
            konta[transakcja.konto_id],
            konta[transakcja.konto_docelowe_id] if czy_przelew else "",
            kategorie.get(transakcja.kategoria_id, ""),
        ]
