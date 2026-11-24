"""Kategoria wydatków albo przychodów."""

from dataclasses import dataclass


@dataclass
class Kategoria:
    """Nazwana grupa transakcji."""

    nazwa: str
    czy_wydatek: bool = True
    id: int | None = None

    def __str__(self) -> str:
        return self.nazwa
