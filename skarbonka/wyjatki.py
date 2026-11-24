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


class NieZnalezionoRekordu(BladSkarbonki):
    """Rekord o podanym numerze nie istnieje."""


class RekordWUzyciu(BladSkarbonki):
    """Rekordu nie można usunąć, bo coś z niego korzysta."""


class BladBazy(BladSkarbonki):
    """Operacja na bazie danych się nie powiodła."""


class UszkodzonaBaza(BladBazy):
    """Plik bazy istnieje, ale nie da się go odczytać."""


class BladPliku(BladSkarbonki):
    """Pliku nie da się odczytać albo zapisać."""


class UszkodzonyPlik(BladPliku):
    """Plik istnieje, ale ma nieprawidłową zawartość."""


class ZaMaloDanych(BladSkarbonki):
    """Historia jest zbyt krótka, żeby coś policzyć."""


class BladKursu(BladSkarbonki):
    """Nie udało się ustalić kursu waluty."""


class BrakKursu(BladKursu):
    """Z podanego dnia nie ma kursu, np. w weekend."""


class AnulowanoOperacje(BladSkarbonki):
    """Użytkownik świadomie przerwał wpisywanie danych."""
