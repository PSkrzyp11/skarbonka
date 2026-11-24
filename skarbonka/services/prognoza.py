"""Prognoza salda na koniec miesiąca."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from skarbonka.services.analizy import z_miesiaca
from skarbonka.services.cykliczne import SerwisCyklicznych
from skarbonka.services.konta import SerwisKont
from skarbonka.services.transakcje import SerwisTransakcji, suma_wydatkow
from skarbonka.utils.daty import dni_miesiaca, przesun_miesiac
from skarbonka.wyjatki import ZaMaloDanych

GROSZ = Decimal("0.01")


@dataclass
class Prognoza:
    """Składniki prognozy i trzy warianty salda."""

    saldo_dzis: Decimal
    cykliczne: Decimal
    dni: int
    koniec: date
    tempo_min: Decimal
    tempo_srednie: Decimal
    tempo_maks: Decimal

    def _saldo(self, tempo: Decimal) -> Decimal:
        """Zwraca saldo końcowe przy podanym dziennym tempie wydatków."""
        return (self.saldo_dzis + self.cykliczne - tempo * self.dni).quantize(GROSZ)

    @property
    def optymistyczna(self) -> Decimal:
        """Saldo, gdy będzie jak w najtańszym miesiącu."""
        return self._saldo(self.tempo_min)

    @property
    def realistyczna(self) -> Decimal:
        """Saldo, gdy będzie jak w przeciętnym miesiącu."""
        return self._saldo(self.tempo_srednie)

    @property
    def pesymistyczna(self) -> Decimal:
        """Saldo, gdy będzie jak w najdroższym miesiącu."""
        return self._saldo(self.tempo_maks)


class SerwisPrognozy:
    """Liczy prognozę z sald, transakcji cyklicznych i historii wydatków."""

    def __init__(
        self, transakcje: SerwisTransakcji, konta: SerwisKont, cykliczne: SerwisCyklicznych
    ) -> None:
        self._transakcje = transakcje
        self._konta = konta
        self._cykliczne = cykliczne

    def policz(self, dzis: date | None = None, miesiace: int = 3) -> Prognoza:
        """Zwraca prognozę na koniec bieżącego miesiąca.

        Wydatki cykliczne są liczone osobno, więc nie wchodzą do tempa.
        Przyszłych przychodów spoza transakcji cyklicznych nie zgadujemy.
        """
        dzis = dzis or date.today()
        koniec = dzis.replace(day=dni_miesiaca(dzis.year, dzis.month))
        tempa = self._tempa(dzis, miesiace)
        return Prognoza(
            saldo_dzis=self._konta.saldo(),
            cykliczne=self._cykliczne.suma_do(koniec),
            dni=(koniec - dzis).days,
            koniec=koniec,
            tempo_min=min(tempa),
            tempo_srednie=sum(tempa) / len(tempa),
            tempo_maks=max(tempa),
        )

    def _tempa(self, dzis: date, miesiace: int) -> list[Decimal]:
        """Zwraca dzienne tempo wydatków w poprzednich miesiącach z historią."""
        wszystkie = self._transakcje.wszystkie()
        tempa = []
        for i in range(1, miesiace + 1):
            miesiac = przesun_miesiac(dzis.replace(day=1), -i)
            z_historii = z_miesiaca(wszystkie, miesiac)
            if not z_historii:
                continue
            zmienne = [t for t in z_historii if t.cykliczna_id is None]
            tempa.append(suma_wydatkow(zmienne) / dni_miesiaca(miesiac.year, miesiac.month))
        if not tempa:
            raise ZaMaloDanych(
                "Prognoza wymaga transakcji z co najmniej jednego poprzedniego miesiąca."
            )
        return tempa
