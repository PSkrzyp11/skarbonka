"""Ikony z systemowej czcionki Windows i dobieranie ich do kategorii."""

DOM = ""
STRZALKI = ""
LISTA = ""
KALENDARZ = ""
WYKRES = ""
FOLDER = ""
USTAWIENIA = ""
PLUS = ""
LUPA = ""
KOSZ = ""
OLOWEK = ""
POBIERZ = ""
WYSLIJ = ""
COFNIJ = ""
ODSWIEZ = ""
ZAMKNIJ = ""
W_LEWO = ""
W_PRAWO = ""
OSTRZEZENIE = ""
PTASZEK = ""
GOTOWE = ""
KARTA = ""
TORBA = ""
WOZEK = ""
AUTO = ""
ZDROWIE = ""
FILM = ""
METKA = ""
TECZKA = ""
POWTARZANIE = ""
FLAGA = ""
KOLO = ""
SLONCE = ""
KSIEZYC = ""
GLOBUS = ""
DOKUMENT = ""
BANK = ""
NAUKA = ""
JEDZENIE = ""
SAMOLOT = ""
GRA = ""
NARZEDZIA = ""
ARCHIWUM = ""
HISTORIA = ""
ZEGAR = ""
KSIAZKA = ""
W_GORE = ""
W_DOL = ""
OSOBA = ""
LUDZIE = ""

SLOWA_KLUCZOWE = {
    "elektr": DOKUMENT,
    "prąd": DOKUMENT,
    "ubezp": DOKUMENT,
    "kredyt": BANK,
    "rata": BANK,
    "jedzeni": JEDZENIE,
    "spożyw": WOZEK,
    "zakup": WOZEK,
    "restaur": JEDZENIE,
    "mieszkan": DOM,
    "dom": DOM,
    "czynsz": DOM,
    "rachun": DOKUMENT,
    "transport": AUTO,
    "auto": AUTO,
    "paliw": AUTO,
    "zdrow": ZDROWIE,
    "lek": ZDROWIE,
    "sport": ZDROWIE,
    "rozryw": FILM,
    "kino": FILM,
    "gry": GRA,
    "ubra": TORBA,
    "odzież": TORBA,
    "wynagrodz": TECZKA,
    "pensja": TECZKA,
    "prac": TECZKA,
    "podróż": SAMOLOT,
    "wakac": SAMOLOT,
    "nauk": NAUKA,
    "szko": NAUKA,
    "studi": NAUKA,
    "książ": KSIAZKA,
    "napraw": NARZEDZIA,
    "osob": OSOBA,
    "internet": GLOBUS,
    "telefon": GLOBUS,
    "netflix": FILM,
    "spotify": FILM,
}


def dla_nazwy(nazwa: str, domyslna: str = METKA) -> str:
    """Dobiera ikonę do nazwy kategorii, celu albo stałej pozycji."""
    mala = nazwa.casefold()
    return next((ikona for slowo, ikona in SLOWA_KLUCZOWE.items() if slowo in mala), domyslna)
