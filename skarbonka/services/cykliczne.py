"""Transakcje cykliczne: zaległości i księgowanie."""

import logging
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

from skarbonka.models.cykliczna import Cykliczna
from skarbonka.models.transakcja import ZERO, Transakcja
from skarbonka.services.transakcje import SerwisTransakcji
from skarbonka.storage.baza import Baza
from skarbonka.storage.repozytoria_planu import RepozytoriumCyklicznych
from skarbonka.utils.walidacja import sprawdz_unikalnosc
from skarbonka.wyjatki import NieprawidlowaData

logger = logging.getLogger(__name__)

NAJSTARSZY_START = timedelta(days=366)


class SerwisCyklicznych:
    """Zasady dotyczące transakcji cyklicznych."""

    def __init__(
        self, baza: Baza, cykliczne: RepozytoriumCyklicznych, transakcje: SerwisTransakcji
    ) -> None:
        self._baza = baza
        self._cykliczne = cykliczne
        self._transakcje = transakcje

    def wszystkie(self) -> list[Cykliczna]:
        """Zwraca wszystkie transakcje cykliczne."""
        return self._cykliczne.wszystkie()

    def sprawdz_nazwe(self, nazwa: str) -> None:
        """Zgłasza błąd, gdy nazwa jest już zajęta."""
        sprawdz_unikalnosc(nazwa, {c.nazwa for c in self.wszystkie()})

    def dodaj(self, cykliczna: Cykliczna, dzis: date | None = None) -> Cykliczna:
        """Dodaje transakcję cykliczną o niepowtarzalnej nazwie."""
        self.sprawdz_nazwe(cykliczna.nazwa)
        if cykliczna.start < (dzis or date.today()) - NAJSTARSZY_START:
            raise NieprawidlowaData("Pierwszy termin może być najwyżej rok wstecz.")
        return self._cykliczne.dodaj(cykliczna)

    def przelacz(self, cykliczna: Cykliczna) -> Cykliczna:
        """Włącza albo wyłącza transakcję cykliczną."""
        zmieniona = replace(cykliczna, aktywna=not cykliczna.aktywna)
        self._cykliczne.zmien(zmieniona)
        return zmieniona

    def usun(self, cykliczna: Cykliczna) -> None:
        """Usuwa wzór. Zaksięgowane wcześniej transakcje zostają."""
        self._cykliczne.usun(cykliczna.id)

    def zalegle(self, dzis: date | None = None) -> list[tuple[Cykliczna, date]]:
        """Zwraca niezaksięgowane terminy do dziś, od najstarszego."""
        dzis = dzis or date.today()
        pary = [
            (cykliczna, termin)
            for cykliczna in self.wszystkie()
            if cykliczna.aktywna
            for termin in cykliczna.niezaksiegowane(dzis)
        ]
        return sorted(pary, key=lambda para: para[1])

    def zaksieguj(self, cykliczna: Cykliczna, termin: date) -> Transakcja:
        """Dodaje transakcję i zapamiętuje jej termin. Całość albo nic."""
        with self._baza.transakcja():
            transakcja = self._transakcje.dodaj(cykliczna.utworz_transakcje(termin))
            self.pomin(cykliczna, termin)
        logger.info("Zaksięgowano %s z dnia %s", cykliczna.nazwa, termin)
        return transakcja

    def pomin(self, cykliczna: Cykliczna, termin: date) -> None:
        """Uznaje termin za załatwiony bez dodawania transakcji."""
        self._cykliczne.zmien(replace(cykliczna, ostatnia=termin))

    def suma_do(self, koniec: date) -> Decimal:
        """Zwraca łączny wpływ niezaksięgowanych terminów do podanego dnia."""
        return sum(
            (
                cykliczna.wplyw
                for cykliczna in self.wszystkie()
                if cykliczna.aktywna
                for _ in cykliczna.niezaksiegowane(koniec)
            ),
            ZERO,
        )
