"""Własne wyjątki aplikacji.

Wszystkie dziedziczą po BladSkarbonki, dzięki czemu interfejs może złapać
każdy przewidziany błąd jednym blokiem except.
"""


class BladSkarbonki(Exception):
    """Klasa bazowa wszystkich przewidzianych błędów aplikacji."""


class BladWalidacji(BladSkarbonki):
    """Dane wejściowe są niepoprawne."""


class NieprawidlowaKwota(BladWalidacji):
    """Tekst nie jest poprawną kwotą albo kwota jest spoza zakresu."""


class NieprawidlowaData(BladWalidacji):
    """Tekst nie jest poprawną datą albo data jest spoza zakresu."""


class AnulowanoOperacje(BladSkarbonki):
    """Użytkownik świadomie przerwał wpisywanie danych."""
