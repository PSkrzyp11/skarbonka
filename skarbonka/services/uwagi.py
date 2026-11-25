"""Sprawy, które wymagają uwagi użytkownika."""

from dataclasses import dataclass
from datetime import date

from skarbonka.services.zestaw import Serwisy
from skarbonka.utils.formatowanie import formatuj_procent

PLAN, STALE = "Plan", "Stałe płatności"


@dataclass(frozen=True)
class Uwaga:
    """Ostrzeżenie, dział, w którym można się nim zająć, i liczba spraw."""

    tekst: str
    dzial: str = PLAN
    ile: int = 1

    def __str__(self) -> str:
        return self.tekst


def zbierz_uwagi(serwisy: Serwisy, dzis: date | None = None) -> list[Uwaga]:
    """Zwraca ostrzeżenia o budżetach, zaległościach i celach po terminie."""
    dzis = dzis or date.today()
    uwagi = [
        Uwaga(f"Budżet {w.kategoria}: {w.stan}, wykorzystano {formatuj_procent(w.procent)}.")
        for w in serwisy.budzety.ostrzezenia(dzis)
    ]
    zalegle = len(serwisy.cykliczne.zalegle(dzis))
    if zalegle:
        uwagi.append(Uwaga(f"Stałe płatności do zaksięgowania: {zalegle}.", STALE, zalegle))
    uwagi.extend(
        Uwaga(f"Minął termin celu {cel.nazwa}.")
        for cel in serwisy.cele.wszystkie()
        if cel.brakuje and cel.termin < dzis
    )
    return uwagi
