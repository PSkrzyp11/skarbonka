"""Salda kont i zasady ich usuwania."""

from decimal import Decimal

from skarbonka.models.konto import Konto
from skarbonka.models.transakcja import ZERO, Transakcja
from skarbonka.services import rekordy
from skarbonka.wyjatki import RekordWUzyciu


def saldo(konta: list[Konto], transakcje: list[Transakcja], konto_id: int | None = None) -> Decimal:
    """Zwraca saldo wybranego konta, a bez konto_id – wszystkich kont razem."""
    wybrane = [k for k in konta if konto_id is None or k.id == konto_id]
    return sum((_saldo_konta(k, transakcje) for k in wybrane), ZERO)


def _saldo_konta(konto: Konto, transakcje: list[Transakcja]) -> Decimal:
    """Zwraca saldo początkowe powiększone o wpływ transakcji."""
    zmiany = sum((t.wplyw_na_konto(konto.id) for t in transakcje), ZERO)
    return konto.saldo_poczatkowe + zmiany


def usun_konto(konta: list[Konto], konto: Konto, transakcje: list[Transakcja]) -> None:
    """Usuwa konto, o ile nie ma na nim żadnych transakcji."""
    uzycia = len([t for t in transakcje if t.dotyczy_konta(konto.id)])
    if uzycia:
        raise RekordWUzyciu(f"Nie można usunąć konta. Liczba jego transakcji: {uzycia}.")
    rekordy.usun(konta, konto.id)
