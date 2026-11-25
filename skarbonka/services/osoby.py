"""Osoby, do których należą stałe przychody i opłaty."""

import logging
from dataclasses import replace

from skarbonka.models.osoba import Osoba
from skarbonka.storage.repozytoria_planu import RepozytoriumOsob
from skarbonka.utils.walidacja import sprawdz_unikalnosc

logger = logging.getLogger(__name__)

WSZYSCY, WSPOLNE = "Wszyscy", "Wspólne"


class SerwisOsob:
    """Zasady dotyczące osób."""

    def __init__(self, osoby: RepozytoriumOsob) -> None:
        self._osoby = osoby

    def wszystkie(self) -> list[Osoba]:
        """Zwraca wszystkie osoby."""
        return self._osoby.wszystkie()

    def pobierz(self, numer: int) -> Osoba:
        """Zwraca osobę o podanym numerze."""
        return self._osoby.pobierz(numer)

    def nazwy(self) -> dict[int, str]:
        """Zwraca słownik: numer osoby -> nazwa."""
        return {osoba.id: osoba.nazwa for osoba in self.wszystkie()}

    def wybor(self) -> dict[str, int | None]:
        """Zwraca słownik: nazwa -> numer. Wspólne pozycje nie mają numeru."""
        return {WSPOLNE: None} | {osoba.nazwa: osoba.id for osoba in self.wszystkie()}

    def sprawdz_nazwe(self, nazwa: str, pomin_id: int | None = None) -> None:
        """Zgłasza błąd, gdy nazwa jest już zajęta."""
        zajete = {osoba.nazwa for osoba in self.wszystkie() if osoba.id != pomin_id}
        sprawdz_unikalnosc(nazwa, zajete | {WSZYSCY, WSPOLNE})

    def dodaj(self, nazwa: str) -> Osoba:
        """Dodaje osobę o niepowtarzalnej nazwie."""
        self.sprawdz_nazwe(nazwa)
        return self._osoby.dodaj(Osoba(nazwa))

    def zmien(self, osoba: Osoba, nazwa: str) -> None:
        """Zmienia nazwę osoby."""
        self.sprawdz_nazwe(nazwa, osoba.id)
        self._osoby.zmien(replace(osoba, nazwa=nazwa))

    def usun(self, osoba: Osoba) -> None:
        """Usuwa osobę razem z jej stałymi pozycjami. Transakcje zostają."""
        self._osoby.usun(osoba.id)
        logger.info("Usunięto osobę nr %s", osoba.id)
