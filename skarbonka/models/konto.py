"""Konto, na którym leżą pieniądze."""

from dataclasses import dataclass
from decimal import Decimal

from skarbonka.models.enums import TypKonta


@dataclass
class Konto:
    """Konto w złotych. Bieżące saldo liczy się z transakcji."""

    nazwa: str
    typ: TypKonta
    saldo_poczatkowe: Decimal = Decimal("0.00")
    id: int | None = None

    def __str__(self) -> str:
        return f"{self.nazwa} ({self.typ})"
