"""Analizy transakcji: podsumowanie miesiąca i największe wydatki."""

from datetime import date
from decimal import Decimal

from skarbonka.models.transakcja import Transakcja, Wydatek
from skarbonka.services.transakcje import saldo, suma_przychodow, suma_wydatkow


def z_miesiaca(transakcje: list[Transakcja], miesiac: date) -> list[Transakcja]:
    """Zwraca transakcje z tego samego miesiąca i roku co podana data."""
    return [
        t
        for t in transakcje
        if (t.data.year, t.data.month) == (miesiac.year, miesiac.month)
    ]


def podsumowanie_miesiaca(transakcje: list[Transakcja], miesiac: date) -> dict[str, Decimal]:
    """Zwraca sumy przychodów i wydatków oraz bilans miesiąca."""
    wybrane = z_miesiaca(transakcje, miesiac)
    return {
        "Przychody": suma_przychodow(wybrane),
        "Wydatki": suma_wydatkow(wybrane),
        "Bilans": saldo(wybrane),
    }


def stopa_oszczednosci(przychody: Decimal, bilans: Decimal) -> float | None:
    """Zwraca, jaki procent przychodów został. None, gdy nie było przychodów."""
    if przychody == 0:
        return None
    return float(bilans / przychody * 100)


def najwieksze_wydatki(transakcje: list[Transakcja], ile: int = 5) -> list[Transakcja]:
    """Zwraca największe wydatki, od najdroższego."""
    wydatki = [t for t in transakcje if isinstance(t, Wydatek)]
    return sorted(wydatki, key=lambda t: t.kwota, reverse=True)[:ile]
