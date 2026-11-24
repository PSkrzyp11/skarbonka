"""Wspólne operacje na listach obiektów z numerem id."""

from typing import Any

from skarbonka.wyjatki import BladWalidacji, NieZnalezionoRekordu


def dodaj(rekordy: list[Any], nowy: Any) -> None:
    """Nadaje obiektowi kolejny numer i dopisuje go do listy."""
    nowy.id = max((r.id for r in rekordy), default=0) + 1
    rekordy.append(nowy)


def znajdz(rekordy: list[Any], numer: int) -> Any:
    """Zwraca obiekt o podanym numerze."""
    for rekord in rekordy:
        if rekord.id == numer:
            return rekord
    raise NieZnalezionoRekordu(f"Nie ma pozycji o numerze {numer}.")


def zmien(rekordy: list[Any], zmieniony: Any) -> None:
    """Zastępuje obiekt nową wersją o tym samym numerze."""
    miejsce = rekordy.index(znajdz(rekordy, zmieniony.id))
    rekordy[miejsce] = zmieniony


def usun(rekordy: list[Any], numer: int) -> None:
    """Usuwa obiekt o podanym numerze."""
    rekordy.remove(znajdz(rekordy, numer))


def sprawdz_nazwe(rekordy: list[Any], nazwa: str) -> None:
    """Pilnuje, aby nazwa się nie powtarzała (wielkość liter nie ma znaczenia)."""
    zajete = {r.nazwa.casefold() for r in rekordy}
    if nazwa.casefold() in zajete:
        raise BladWalidacji(f"Nazwa „{nazwa}” jest już zajęta.")
