"""Typy wyliczeniowe, czyli zamknięte listy dozwolonych wartości."""

from enum import Enum


class TypKonta(Enum):
    """Rodzaj konta."""

    GOTOWKA = "gotówka"
    BIEZACE = "konto bieżące"
    OSZCZEDNOSCI = "konto oszczędnościowe"

    def __str__(self) -> str:
        return self.value


class StanBudzetu(Enum):
    """Ocena wykorzystania budżetu."""

    W_NORMIE = "w normie"
    UWAGA = "blisko limitu"
    PRZEKROCZONY = "przekroczony"

    def __str__(self) -> str:
        return self.value


class Czestotliwosc(Enum):
    """Jak często powtarza się transakcja cykliczna."""

    TYDZIEN = "co tydzień"
    MIESIAC = "co miesiąc"
    KWARTAL = "co kwartał"
    ROK = "co rok"

    def __str__(self) -> str:
        return self.value


class StanPlatnosci(Enum):
    """Co dzieje się z terminem stałej płatności."""

    ZALATWIONA = "załatwiona"
    CZEKA = "czeka"
    NADCHODZI = "nadchodzi"

    def __str__(self) -> str:
        return self.value
