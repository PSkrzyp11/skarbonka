"""Osoba, która ma własne stałe przychody i opłaty."""

from dataclasses import dataclass


@dataclass
class Osoba:
    """Domownik, np. partner albo współlokator."""

    nazwa: str
    id: int | None = None

    def __str__(self) -> str:
        return self.nazwa
