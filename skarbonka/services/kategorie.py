"""Kategorie: zestaw startowy, wybór pasujących i usuwanie."""

from skarbonka.config import KATEGORIE_PRZYCHODOW, KATEGORIE_WYDATKOW
from skarbonka.models.kategoria import Kategoria
from skarbonka.models.transakcja import Przychod, Transakcja, Wydatek
from skarbonka.services import rekordy
from skarbonka.wyjatki import RekordWUzyciu


def domyslne_kategorie() -> list[Kategoria]:
    """Tworzy zestaw kategorii na start."""
    wynik: list[Kategoria] = []
    for czy_wydatek, nazwy in ((True, KATEGORIE_WYDATKOW), (False, KATEGORIE_PRZYCHODOW)):
        for nazwa in nazwy:
            rekordy.dodaj(wynik, Kategoria(nazwa, czy_wydatek))
    return wynik


def pasujace(kategorie: list[Kategoria], rodzaj: type[Transakcja]) -> list[Kategoria]:
    """Zwraca kategorie właściwe dla wydatków, przychodów albo żadne dla przelewów."""
    if issubclass(rodzaj, Wydatek):
        return [k for k in kategorie if k.czy_wydatek]
    if issubclass(rodzaj, Przychod):
        return [k for k in kategorie if not k.czy_wydatek]
    return []


def usun_kategorie(
    kategorie: list[Kategoria], kategoria: Kategoria, transakcje: list[Transakcja]
) -> None:
    """Usuwa kategorię, o ile nie korzysta z niej żadna transakcja."""
    uzycia = len([t for t in transakcje if t.kategoria_id == kategoria.id])
    if uzycia:
        raise RekordWUzyciu(f"Nie można usunąć kategorii. Liczba jej transakcji: {uzycia}.")
    rekordy.usun(kategorie, kategoria.id)
