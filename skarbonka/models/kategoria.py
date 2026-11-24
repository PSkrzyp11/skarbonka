"""Kategoria transakcji i reguła, która ją przypisuje."""

from dataclasses import dataclass


@dataclass
class Kategoria:
    """Nazwana grupa transakcji."""

    nazwa: str
    czy_wydatek: bool = True
    id: int | None = None

    def __str__(self) -> str:
        return self.nazwa


@dataclass
class Regula:
    """Przypisuje kategorię, gdy opis zawiera podaną frazę."""

    fraza: str
    kategoria_id: int
    priorytet: int = 0
    id: int | None = None

    def pasuje(self, opis: str) -> bool:
        """Sprawdza, czy opis zawiera frazę (wielkość liter nie ma znaczenia)."""
        return self.fraza.casefold() in opis.casefold()

    def __str__(self) -> str:
        return self.fraza
