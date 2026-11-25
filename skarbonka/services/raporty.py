"""Raport miesiąca w pliku tekstowym."""

import logging
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from skarbonka.services import analizy
from skarbonka.services.cykliczne import SerwisCyklicznych
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
        cykliczne: SerwisCyklicznych,
    ) -> None:
        self._transakcje = transakcje
        self._konta = konta
        self._kategorie = kategorie
        self._budzety = budzety
        self._cele = cele
        self._cykliczne = cykliczne

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

        podsumowanie = [self._linia(nazwa, kwota) for nazwa, kwota in sumy.items()]
        podsumowanie.append(analizy.opis_oszczednosci(sumy["Przychody"], sumy["Bilans"]))
        yield from self._sekcja("Podsumowanie", podsumowanie)

        kwoty = analizy.wydatki_wg_kategorii(transakcje, self._kategorie.wszystkie())
        procenty = analizy.udzialy(kwoty).values()
        yield from self._sekcja(
            "Wydatki według kategorii",
            [
                f"{self._linia(nazwa, kwota)} {formatuj_procent(procent):>8}"
                for (nazwa, kwota), procent in zip(kwoty.items(), procenty)
            ],
        )
        yield from self._sekcja(
            "Budżety",
            [
                f"{self._linia(w.kategoria, w.wydano)} z {formatuj_kwote(w.budzet.limit)}, {w.stan}"
                for w in self._budzety.wykonanie(miesiac)
            ],
        )
        yield from self._sekcja("Stałe pozycje, przeliczone na miesiąc", self._stale())
        yield from self._sekcja(
            "Największe wydatki",
            [
                f"{formatuj_date(w.data)} {self._linia(w.opis, w.kwota)}"
                for w in analizy.najwieksze_wydatki(transakcje)
            ],
        )
        yield from self._sekcja(
            "Cele oszczędnościowe",
            [
                f"{self._linia(cel.nazwa, cel.odlozono)} {formatuj_procent(cel.procent):>8}"
                for cel in self._cele.wszystkie()
            ],
        )
        salda = [self._linia(k.nazwa, self._konta.saldo(k.id)) for k in self._konta.wszystkie()]
        salda.append(self._linia("Razem", self._konta.saldo()))
        yield from self._sekcja("Salda kont w dniu utworzenia raportu", salda)

    def _stale(self) -> list[str]:
        """Zwraca linie stałych pozycji i kwotę, która zostaje na czysto."""
        aktywne = [c for c in self._cykliczne.wszystkie() if c.aktywna]
        if not aktywne:
            return []
        linie = [self._linia(c.nazwa, c.miesiecznie) for c in aktywne]
        return [*linie, self._linia("Zostaje na czysto", self._cykliczne.bilans().na_czysto)]

    @staticmethod
    def _sekcja(tytul: str, linie: list[str]) -> Iterator[str]:
        """Generator: oddaje nagłówek i linie sekcji albo słowo „brak”."""
        yield from ("", tytul, "-" * SZEROKOSC)
        yield from (linia for linia in linie or ["brak"] if linia)

    @staticmethod
    def _linia(nazwa: str, kwota: Decimal) -> str:
        """Zwraca nazwę i kwotę wyrównane w kolumnach."""
        return f"{nazwa:<30} {formatuj_kwote(kwota):>16}"
