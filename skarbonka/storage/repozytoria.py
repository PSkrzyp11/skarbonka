"""Repozytoria, czyli jedyne miejsce, przez które sięga się po zapisane dane."""

from typing import Generic, TypeVar

from skarbonka.wyjatki import NieZnalezionoRekordu

T = TypeVar("T")


class Repozytorium(Generic[T]):
    """Przechowuje w pamięci obiekty z polem id."""

    def __init__(self) -> None:
        self._rekordy: dict[int, T] = {}
        self._ostatni_id = 0

    def __len__(self) -> int:
        return len(self._rekordy)

    def wszystkie(self) -> list[T]:
        """Zwraca wszystkie obiekty w kolejności dodania."""
        return list(self._rekordy.values())

    def pobierz(self, numer: int) -> T:
        """Zwraca obiekt o podanym numerze."""
        try:
            return self._rekordy[numer]
        except KeyError:
            raise NieZnalezionoRekordu(f"Nie ma pozycji o numerze {numer}.") from None

    def dodaj(self, rekord: T) -> T:
        """Nadaje obiektowi kolejny numer i go zapisuje."""
        self._ostatni_id += 1
        rekord.id = self._ostatni_id
        self._rekordy[rekord.id] = rekord
        return rekord

    def zmien(self, rekord: T) -> None:
        """Zastępuje zapisany obiekt nową wersją o tym samym numerze."""
        self.pobierz(rekord.id)
        self._rekordy[rekord.id] = rekord

    def usun(self, numer: int) -> None:
        """Usuwa obiekt o podanym numerze."""
        self.pobierz(numer)
        del self._rekordy[numer]
