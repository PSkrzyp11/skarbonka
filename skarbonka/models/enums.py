"""Typy wyliczeniowe, czyli zamknięte listy dozwolonych wartości."""

from enum import Enum


class TypKonta(Enum):
    """Rodzaj konta."""

    GOTOWKA = "gotówka"
    BIEZACE = "konto bieżące"
    OSZCZEDNOSCI = "konto oszczędnościowe"

    def __str__(self) -> str:
        return self.value
