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
    """Jednostka, w której powtarza się stała pozycja."""

    DZIEN = "co dzień"
    TYDZIEN = "co tydzień"
    MIESIAC = "co miesiąc"
    KWARTAL = "co kwartał"
    ROK = "co rok"

    def odmiana(self, ile: int) -> str:
        """Zwraca nazwę jednostki pasującą do liczby, np. 2 miesiące, 5 miesięcy."""
        jeden, dwa, piec = ODMIANY[self]
        if ile == 1:
            return jeden
        return dwa if ile % 10 in (2, 3, 4) and ile % 100 not in (12, 13, 14) else piec

    def okres(self, ile: int) -> str:
        """Zwraca odstęp słowami, np. 2 miesiące."""
        return f"{ile} {self.odmiana(ile)}"

    @classmethod
    def z_odmiany(cls, slowo: str) -> "Czestotliwosc":
        """Rozpoznaje jednostkę po dowolnej formie jej nazwy."""
        return next(jednostka for jednostka, formy in ODMIANY.items() if slowo in formy)

    def __str__(self) -> str:
        return self.value


ODMIANY = {
    Czestotliwosc.DZIEN: ("dzień", "dni", "dni"),
    Czestotliwosc.TYDZIEN: ("tydzień", "tygodnie", "tygodni"),
    Czestotliwosc.MIESIAC: ("miesiąc", "miesiące", "miesięcy"),
    Czestotliwosc.KWARTAL: ("kwartał", "kwartały", "kwartałów"),
    Czestotliwosc.ROK: ("rok", "lata", "lat"),
}


class StanPlatnosci(Enum):
    """Co dzieje się z terminem stałej płatności."""

    ZALATWIONA = "załatwiona"
    CZEKA = "czeka"
    NADCHODZI = "nadchodzi"

    def __str__(self) -> str:
        return self.value
