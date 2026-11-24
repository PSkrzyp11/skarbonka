"""Kategorie: dodawanie, usuwanie i wybór pasujących do transakcji."""

from skarbonka.models.kategoria import Kategoria
from skarbonka.models.transakcja import Przychod, Transakcja, Wydatek
from skarbonka.storage.repozytoria import Repozytorium
from skarbonka.utils.walidacja import sprawdz_unikalnosc
from skarbonka.wyjatki import RekordWUzyciu


class SerwisKategorii:
    """Zasady dotyczące kategorii."""

    def __init__(
        self, kategorie: Repozytorium[Kategoria], transakcje: Repozytorium[Transakcja]
    ) -> None:
        self._kategorie = kategorie
        self._transakcje = transakcje

    def wszystkie(self) -> list[Kategoria]:
        """Zwraca wszystkie kategorie."""
        return self._kategorie.wszystkie()

    def pobierz(self, numer: int) -> Kategoria:
        """Zwraca kategorię o podanym numerze."""
        return self._kategorie.pobierz(numer)

    def nazwy(self) -> dict[int, str]:
        """Zwraca słownik: numer kategorii -> nazwa."""
        return {k.id: k.nazwa for k in self.wszystkie()}

    def pasujace(self, rodzaj: type[Transakcja]) -> list[Kategoria]:
        """Zwraca kategorie właściwe dla wydatków, przychodów albo żadne dla przelewów."""
        if issubclass(rodzaj, Wydatek):
            return [k for k in self.wszystkie() if k.czy_wydatek]
        if issubclass(rodzaj, Przychod):
            return [k for k in self.wszystkie() if not k.czy_wydatek]
        return []

    def sprawdz_nazwe(self, nazwa: str) -> None:
        """Zgłasza błąd, gdy nazwa jest już zajęta."""
        sprawdz_unikalnosc(nazwa, {k.nazwa for k in self.wszystkie()})

    def dodaj(self, nazwa: str, czy_wydatek: bool = True) -> Kategoria:
        """Dodaje kategorię o niepowtarzalnej nazwie."""
        self.sprawdz_nazwe(nazwa)
        return self._kategorie.dodaj(Kategoria(nazwa, czy_wydatek))

    def usun(self, kategoria: Kategoria) -> None:
        """Usuwa kategorię, o ile nie korzysta z niej żadna transakcja."""
        uzycia = len([t for t in self._transakcje.wszystkie() if t.kategoria_id == kategoria.id])
        if uzycia:
            raise RekordWUzyciu(f"Nie można usunąć kategorii. Liczba jej transakcji: {uzycia}.")
        self._kategorie.usun(kategoria.id)
