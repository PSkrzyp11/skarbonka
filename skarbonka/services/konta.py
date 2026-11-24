"""Konta: dodawanie, usuwanie i salda."""

from decimal import Decimal

from skarbonka.models.enums import TypKonta
from skarbonka.models.konto import Konto
from skarbonka.models.transakcja import ZERO, Transakcja
from skarbonka.storage.repozytoria import Repozytorium
from skarbonka.utils.walidacja import sprawdz_unikalnosc
from skarbonka.wyjatki import RekordWUzyciu


class SerwisKont:
    """Zasady dotyczące kont."""

    def __init__(
        self, konta: Repozytorium[Konto], transakcje: Repozytorium[Transakcja]
    ) -> None:
        self._konta = konta
        self._transakcje = transakcje

    def wszystkie(self) -> list[Konto]:
        """Zwraca wszystkie konta."""
        return self._konta.wszystkie()

    def pobierz(self, numer: int) -> Konto:
        """Zwraca konto o podanym numerze."""
        return self._konta.pobierz(numer)

    def nazwy(self) -> dict[int, str]:
        """Zwraca słownik: numer konta -> nazwa."""
        return {k.id: k.nazwa for k in self.wszystkie()}

    def sprawdz_nazwe(self, nazwa: str) -> None:
        """Zgłasza błąd, gdy nazwa jest już zajęta."""
        sprawdz_unikalnosc(nazwa, {k.nazwa for k in self.wszystkie()})

    def dodaj(self, nazwa: str, typ: TypKonta, saldo_poczatkowe: Decimal = ZERO) -> Konto:
        """Dodaje konto o niepowtarzalnej nazwie."""
        self.sprawdz_nazwe(nazwa)
        return self._konta.dodaj(Konto(nazwa, typ, saldo_poczatkowe))

    def usun(self, konto: Konto) -> None:
        """Usuwa konto, o ile nie ma na nim żadnych transakcji."""
        uzycia = len([t for t in self._transakcje.wszystkie() if t.dotyczy_konta(konto.id)])
        if uzycia:
            raise RekordWUzyciu(f"Nie można usunąć konta. Liczba jego transakcji: {uzycia}.")
        self._konta.usun(konto.id)

    def saldo(self, konto_id: int | None = None) -> Decimal:
        """Zwraca saldo wybranego konta, a bez konto_id – wszystkich kont razem."""
        wybrane = [k for k in self.wszystkie() if konto_id is None or k.id == konto_id]
        transakcje = self._transakcje.wszystkie()
        return sum((self._policz_saldo(k, transakcje) for k in wybrane), ZERO)

    @staticmethod
    def _policz_saldo(konto: Konto, transakcje: list[Transakcja]) -> Decimal:
        """Zwraca saldo początkowe powiększone o wpływ transakcji."""
        zmiany = sum((t.wplyw_na_konto(konto.id) for t in transakcje), ZERO)
        return konto.saldo_poczatkowe + zmiany
