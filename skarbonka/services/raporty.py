"""Raport miesiąca w pliku tekstowym."""

import logging
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from skarbonka.services import analizy
from skarbonka.services.kategorie import SerwisKategorii
from skarbonka.services.konta import SerwisKont
from skarbonka.services.planowanie import SerwisBudzetow, SerwisCeli
from skarbonka.services.transakcje import SerwisTransakcji
from skarbonka.utils.formatowanie import (
    formatuj_date,
    formatuj_kwote,
    formatuj_miesiac,
    formatuj_procent,
)
from skarbonka.wyjatki import BladPliku

logger = logging.getLogger(__name__)

SZEROKOSC = 60


class SerwisRaportow:
    """Tworzy raport z podsumowaniem miesiąca."""

    def __init__(
        self,
        transakcje: SerwisTransakcji,
        konta: SerwisKont,
        kategorie: SerwisKategorii,
        budzety: SerwisBudzetow,
        cele: SerwisCeli,
    ) -> None:
        self._transakcje = transakcje
        self._konta = konta
        self._kategorie = kategorie
        self._budzety = budzety
        self._cele = cele

    def zapisz(self, miesiac: date, sciezka: Path) -> None:
        """Zapisuje raport do pliku tekstowego."""
        try:
            sciezka.parent.mkdir(parents=True, exist_ok=True)
            with open(sciezka, "w", encoding="utf-8") as plik:
                for linia in self.linie(miesiac):
                    print(linia, file=plik)
        except (OSError, ValueError) as blad:
            raise BladPliku(f"Nie można zapisać raportu {sciezka}: {blad}") from blad
        logger.info("Zapisano raport %s", sciezka.name)

    def linie(self, miesiac: date) -> Iterator[str]:
        """Generator: oddaje kolejne linie raportu."""
        wszystkie = self._transakcje.wszystkie()
        transakcje = analizy.z_miesiaca(wszystkie, miesiac)
        sumy = analizy.podsumowanie_miesiaca(wszystkie, miesiac)

        yield f"SKARBONKA - raport za {formatuj_miesiac(miesiac)}"
        yield f"Utworzono: {datetime.now():%d.%m.%Y %H:%M}"

        yield from self._naglowek("Podsumowanie")
        yield from (self._linia(nazwa, kwota) for nazwa, kwota in sumy.items())
        stopa = analizy.stopa_oszczednosci(sumy["Przychody"], sumy["Bilans"])
        if stopa is not None:
            yield f"Zaoszczędzono {formatuj_procent(stopa)} przychodów."

        yield from self._naglowek("Wydatki według kategorii")
        kwoty = analizy.wydatki_wg_kategorii(transakcje, self._kategorie.wszystkie())
        for (nazwa, kwota), procent in zip(kwoty.items(), analizy.udzialy(kwoty).values()):
            yield f"{self._linia(nazwa, kwota)} {formatuj_procent(procent):>8}"

        yield from self._naglowek("Budżety")
        for w in self._budzety.wykonanie(miesiac):
            limit = formatuj_kwote(w.budzet.limit)
            yield f"{self._linia(w.kategoria, w.wydano)} z {limit}, {w.stan}"

        yield from self._naglowek("Największe wydatki")
        for wydatek in analizy.najwieksze_wydatki(transakcje):
            yield f"{formatuj_date(wydatek.data)} {self._linia(wydatek.opis, wydatek.kwota)}"

        yield from self._naglowek("Cele oszczędnościowe")
        for cel in self._cele.wszystkie():
            yield f"{self._linia(cel.nazwa, cel.odlozono)} {formatuj_procent(cel.procent):>8}"

        yield from self._naglowek("Salda kont w dniu utworzenia raportu")
        for konto in self._konta.wszystkie():
            yield self._linia(konto.nazwa, self._konta.saldo(konto.id))
        yield self._linia("Razem", self._konta.saldo())

    @staticmethod
    def _naglowek(tytul: str) -> tuple[str, ...]:
        """Zwraca linie nagłówka sekcji."""
        return ("", tytul, "-" * SZEROKOSC)

    @staticmethod
    def _linia(nazwa: str, kwota: Decimal) -> str:
        """Zwraca nazwę i kwotę wyrównane w kolumnach."""
        return f"{nazwa:<30} {formatuj_kwote(kwota):>16}"
