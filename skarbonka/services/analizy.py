"""Analizy transakcji: podsumowania, kategorie, trend i największe wydatki."""

from datetime import date, timedelta
from decimal import Decimal

from skarbonka.models.kategoria import Kategoria
from skarbonka.models.transakcja import ZERO, Transakcja, Wydatek
from skarbonka.services.transakcje import bilans, suma_przychodow, suma_wydatkow
from skarbonka.utils.daty import przesun_miesiac
from skarbonka.utils.formatowanie import formatuj_procent


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
        "Bilans": bilans(wybrane),
    }


def stopa_oszczednosci(przychody: Decimal, zostalo: Decimal) -> float | None:
    """Zwraca, jaki procent przychodów został. None, gdy nie było przychodów."""
    if przychody == 0:
        return None
    return float(zostalo / przychody * 100)


def opis_oszczednosci(przychody: Decimal, zostalo: Decimal) -> str:
    """Zwraca zdanie o oszczędnościach, a bez przychodów pusty tekst."""
    stopa = stopa_oszczednosci(przychody, zostalo)
    if stopa is None:
        return ""
    if stopa < 0:
        return "Wydatki były większe niż przychody."
    return f"Zaoszczędzono {formatuj_procent(stopa)} przychodów."


def wydatki_wg_kategorii(
    transakcje: list[Transakcja], kategorie: list[Kategoria]
) -> dict[str, Decimal]:
    """Zwraca sumy wydatków w kategoriach, od największej. Pomija puste kategorie."""
    sumy = {
        kategoria.nazwa: suma_wydatkow(
            [t for t in transakcje if t.kategoria_id == kategoria.id]
        )
        for kategoria in kategorie
    }
    niepuste = filter(lambda para: para[1] > 0, sumy.items())
    return dict(sorted(niepuste, key=lambda para: para[1], reverse=True))


def udzialy(kwoty: dict[str, Decimal]) -> dict[str, float]:
    """Zamienia kwoty na procenty całości."""
    razem = sum(kwoty.values())
    if razem == 0:
        return {}
    return {nazwa: float(kwota / razem * 100) for nazwa, kwota in kwoty.items()}


def trend(
    transakcje: list[Transakcja], ostatni: date | None = None, ile: int = 6
) -> list[tuple[date, dict[str, Decimal]]]:
    """Zwraca podsumowania kolejnych miesięcy, kończąc na podanym."""
    ostatni = (ostatni or date.today()).replace(day=1)
    miesiace = [przesun_miesiac(ostatni, -i) for i in range(ile - 1, -1, -1)]
    return [(m, podsumowanie_miesiaca(transakcje, m)) for m in miesiace]


def historia_salda(
    transakcje: list[Transakcja], saldo_dzis: Decimal, dzis: date, dni: int = 90
) -> list[tuple[date, Decimal]]:
    """Zwraca łączne saldo na koniec kolejnych dni, od najdawniejszego.

    Liczy wstecz: od dzisiejszego salda odejmuje to, co wydarzyło się później.
    """
    zmiany: dict[date, Decimal] = {}
    for t in transakcje:
        zmiany[t.data] = zmiany.get(t.data, ZERO) + t.wplyw
    wynik = []
    saldo = saldo_dzis
    for i in range(dni + 1):
        dzien = dzis - timedelta(days=i)
        wynik.append((dzien, saldo))
        saldo -= zmiany.get(dzien, ZERO)
    return wynik[::-1]


def najwieksze_wydatki(transakcje: list[Transakcja], ile: int = 5) -> list[Transakcja]:
    """Zwraca największe wydatki, od najdroższego."""
    wydatki = [t for t in transakcje if isinstance(t, Wydatek)]
    return sorted(wydatki, key=lambda t: t.kwota, reverse=True)[:ile]
