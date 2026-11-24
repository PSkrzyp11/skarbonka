"""Sprawy, które wymagają uwagi użytkownika."""

from datetime import date

from skarbonka.services.zestaw import Serwisy
from skarbonka.utils.formatowanie import formatuj_procent


def zbierz_uwagi(serwisy: Serwisy, dzis: date | None = None) -> list[str]:
    """Zwraca ostrzeżenia o budżetach, zaległościach i celach po terminie."""
    dzis = dzis or date.today()
    uwagi = [
        f"Budżet {w.kategoria}: {w.stan}, wykorzystano {formatuj_procent(w.procent)}."
        for w in serwisy.budzety.ostrzezenia(dzis)
    ]
    zalegle = len(serwisy.cykliczne.zalegle(dzis))
    if zalegle:
        uwagi.append(f"Zaległe transakcje cykliczne: {zalegle} (Plan -> Cykliczne).")
    uwagi.extend(
        f"Minął termin celu {cel.nazwa}."
        for cel in serwisy.cele.wszystkie()
        if cel.brakuje and cel.termin < dzis
    )
    return uwagi
