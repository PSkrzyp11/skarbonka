"""Bezpieczne wczytywanie danych z klawiatury.

To jedyne miejsce w aplikacji, które używa funkcji input().
"""

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

from skarbonka.config import MAKS_DLUGOSC_OPISU, SLOWO_ANULUJ
from skarbonka.utils.walidacja import (
    parsuj_date,
    parsuj_kwote,
    parsuj_miesiac,
    parsuj_numer,
    parsuj_tak_nie,
    parsuj_wybor,
    sprawdz_tekst,
)
from skarbonka.wyjatki import AnulowanoOperacje, BladWalidacji, NieZnalezionoRekordu


def wczytaj(komunikat: str, parser: Callable[[str], Any], domyslna: Any = None) -> Any:
    """Pyta użytkownika tak długo, aż parser zaakceptuje odpowiedź.

    Pusta odpowiedź oznacza wartość domyślną (o ile jest podana), a słowo
    „anuluj” przerywa całą operację.
    """
    while True:
        tekst = input(f"{komunikat}: ")
        if tekst.strip().lower() == SLOWO_ANULUJ:
            raise AnulowanoOperacje("Operacja anulowana.")
        if not tekst.strip() and domyslna is not None:
            return domyslna
        try:
            return parser(tekst)
        except BladWalidacji as blad:
            print(f"  ! {blad}")


def wczytaj_kwote(komunikat: str = "Kwota") -> Decimal:
    """Wczytuje dodatnią kwotę."""
    return wczytaj(komunikat, parsuj_kwote)


def wczytaj_saldo(komunikat: str = "Saldo początkowe") -> Decimal:
    """Wczytuje kwotę, która może być też zerem lub liczbą ujemną."""
    return wczytaj(
        f"{komunikat} [0]",
        lambda tekst: parsuj_kwote(tekst, minimum=None),
        domyslna=Decimal("0.00"),
    )


def wczytaj_date(komunikat: str = "Data") -> date:
    """Wczytuje datę nie późniejszą niż dzisiejsza (Enter = dziś)."""
    dzis = date.today()
    return wczytaj(
        f"{komunikat} [{dzis:%d.%m.%Y}]",
        lambda tekst: parsuj_date(tekst, najpozniej=dzis),
        domyslna=dzis,
    )


def wczytaj_miesiac(komunikat: str = "Miesiąc") -> date:
    """Wczytuje miesiąc (Enter = bieżący)."""
    biezacy = date.today().replace(day=1)
    return wczytaj(f"{komunikat} [{biezacy:%m.%Y}]", parsuj_miesiac, domyslna=biezacy)


def wczytaj_tekst(komunikat: str, maks: int = MAKS_DLUGOSC_OPISU) -> str:
    """Wczytuje niepusty tekst."""
    return wczytaj(komunikat, lambda tekst: sprawdz_tekst(tekst, komunikat, maks))


def wczytaj_numer(komunikat: str) -> int:
    """Wczytuje dodatnią liczbę całkowitą."""
    return wczytaj(komunikat, parsuj_numer)


def wczytaj_wybor(komunikat: str, dozwolone: tuple[str, ...]) -> str:
    """Wczytuje jedną z dozwolonych opcji."""
    return wczytaj(komunikat, lambda tekst: parsuj_wybor(tekst, dozwolone))


def wybierz(komunikat: str, elementy: list[Any]) -> Any:
    """Wypisuje numerowaną listę i zwraca wybrany element.

    Gdy element jest tylko jeden, wybiera go bez pytania.
    """
    if not elementy:
        raise NieZnalezionoRekordu(f"{komunikat} – brak pozycji do wyboru.")
    if len(elementy) == 1:
        print(f"{komunikat}: {elementy[0]}")
        return elementy[0]
    for numer, element in enumerate(elementy, start=1):
        print(f"  {numer}) {element}")
    numery = tuple(str(numer) for numer in range(1, len(elementy) + 1))
    return elementy[int(wczytaj_wybor(komunikat, numery)) - 1]


def potwierdz(pytanie: str) -> bool:
    """Zadaje pytanie tak/nie."""
    return wczytaj(f"{pytanie} (t/n)", parsuj_tak_nie)
