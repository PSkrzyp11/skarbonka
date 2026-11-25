"""Stałe przychody i opłaty: bilans miesiąca, harmonogram i księgowanie."""

import logging
from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import Decimal

from skarbonka.models.cykliczna import GROSZ, Cykliczna
from skarbonka.models.enums import StanPlatnosci
from skarbonka.models.transakcja import ZERO, Transakcja
from skarbonka.services.transakcje import SerwisTransakcji
from skarbonka.storage.baza import Baza
from skarbonka.storage.repozytoria_planu import RepozytoriumCyklicznych
from skarbonka.utils.daty import dni_miesiaca
from skarbonka.utils.walidacja import sprawdz_unikalnosc
from skarbonka.wyjatki import NieprawidlowaData

logger = logging.getLogger(__name__)

NAJSTARSZY_START = timedelta(days=366)
SREDNIO_DNI_W_MIESIACU = 30


@dataclass(frozen=True)
class BilansStalych:
    """Stałe przychody i opłaty w przeliczeniu na jeden miesiąc."""

    przychody: Decimal
    wydatki: Decimal

    @property
    def na_czysto(self) -> Decimal:
        """Zwraca kwotę, która zostaje po opłaceniu wszystkiego."""
        return self.przychody - self.wydatki

    @property
    def dziennie(self) -> Decimal:
        """Zwraca kwotę na czysto podzieloną na 30 dni."""
        return (self.na_czysto / SREDNIO_DNI_W_MIESIACU).quantize(GROSZ)

    @property
    def procent(self) -> float | None:
        """Zwraca, jaki procent przychodów zostaje. None, gdy przychodów nie ma."""
        if self.przychody == 0:
            return None
        return float(self.na_czysto / self.przychody * 100)


@dataclass(frozen=True)
class Platnosc:
    """Jeden termin stałej pozycji w harmonogramie."""

    cykliczna: Cykliczna
    termin: date
    stan: StanPlatnosci

    @property
    def kolejna(self) -> bool:
        """Czy to najbliższy niezaksięgowany termin swojej pozycji."""
        return self.termin == self.cykliczna.nastepny


def do_zaplaty(platnosci: list[Platnosc]) -> Decimal:
    """Zwraca sumę opłat z harmonogramu, które nie są jeszcze załatwione."""
    return sum(
        (
            p.cykliczna.kwota
            for p in platnosci
            if p.stan is not StanPlatnosci.ZALATWIONA and p.cykliczna.wplyw < 0
        ),
        ZERO,
    )


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

    def pobierz(self, numer: int) -> Cykliczna:
        """Zwraca transakcję cykliczną o podanym numerze."""
        return self._cykliczne.pobierz(numer)

    def sprawdz_nazwe(self, nazwa: str, pomin_id: int | None = None) -> None:
        """Zgłasza błąd, gdy nazwa jest już zajęta przez inną pozycję."""
        zajete = {c.nazwa for c in self.wszystkie() if c.id != pomin_id}
        sprawdz_unikalnosc(nazwa, zajete)

    def dodaj(self, cykliczna: Cykliczna, dzis: date | None = None) -> Cykliczna:
        """Dodaje transakcję cykliczną o niepowtarzalnej nazwie."""
        self.sprawdz_nazwe(cykliczna.nazwa)
        if cykliczna.start < (dzis or date.today()) - NAJSTARSZY_START:
            raise NieprawidlowaData("Pierwszy termin może być najwyżej rok wstecz.")
        return self._cykliczne.dodaj(cykliczna)

    def zmien(self, zmieniona: Cykliczna) -> None:
        """Zapisuje zmienioną pozycję. Wcześniejsze transakcje zostają bez zmian."""
        self.sprawdz_nazwe(zmieniona.nazwa, zmieniona.id)
        self._cykliczne.zmien(zmieniona)
        logger.info("Zmieniono stałą pozycję %s", zmieniona.nazwa)

    def bilans(self) -> BilansStalych:
        """Zwraca miesięczny bilans aktywnych pozycji."""
        kwoty = [c.miesiecznie for c in self.wszystkie() if c.aktywna]
        return BilansStalych(
            przychody=sum((k for k in kwoty if k > 0), ZERO),
            wydatki=-sum((k for k in kwoty if k < 0), ZERO),
        )

    def harmonogram(self, dzis: date | None = None) -> list[Platnosc]:
        """Zwraca terminy bieżącego miesiąca oraz starsze zaległości."""
        dzis = dzis or date.today()
        poczatek = dzis.replace(day=1)
        koniec = dzis.replace(day=dni_miesiaca(dzis.year, dzis.month))
        platnosci = [
            Platnosc(cykliczna, termin, StanPlatnosci.CZEKA)
            for cykliczna, termin in self.zalegle(dzis)
            if termin < poczatek
        ]
        for cykliczna in self.wszystkie():
            if not cykliczna.aktywna:
                continue
            for termin in cykliczna.terminy(poczatek, koniec):
                stan = self._stan(cykliczna, termin, dzis)
                platnosci.append(Platnosc(cykliczna, termin, stan))
        return sorted(platnosci, key=lambda p: p.termin)

    @staticmethod
    def _stan(cykliczna: Cykliczna, termin: date, dzis: date) -> StanPlatnosci:
        """Ocenia jeden termin."""
        if cykliczna.ostatnia is not None and termin <= cykliczna.ostatnia:
            return StanPlatnosci.ZALATWIONA
        return StanPlatnosci.CZEKA if termin <= dzis else StanPlatnosci.NADCHODZI

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

    def zaksieguj(
        self, cykliczna: Cykliczna, termin: date, dzis: date | None = None
    ) -> Transakcja:
        """Dodaje transakcję i zapamiętuje jej termin. Całość albo nic.

        Płatność zrobiona przed terminem dostaje dzisiejszą datę.
        """
        data = min(termin, dzis or date.today())
        with self._baza.transakcja():
            transakcja = self._transakcje.dodaj(cykliczna.utworz_transakcje(data))
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
