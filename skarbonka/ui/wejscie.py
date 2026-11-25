"""Bezpieczne wczytywanie danych z klawiatury.

To jedyne miejsce w aplikacji, które używa funkcji input().
"""

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from skarbonka.config import (
    MAKS_DLUGOSC_NAZWY,
    MAKS_DLUGOSC_OPISU,
    MAKS_DLUGOSC_SCIEZKI,
    SLOWO_ANULUJ,
)
from skarbonka.ui import widoki
from skarbonka.utils.formatowanie import formatuj_date, formatuj_kwote
from skarbonka.utils.walidacja import (
    parsuj_date,
    parsuj_kurs,
    parsuj_kwote,
    parsuj_liczbe,
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
            widoki.blad(str(blad))


def _z_podpowiedzia(komunikat: str, podpowiedz: str) -> str:
    """Dopisuje do komunikatu wartość, którą wstawi sam Enter."""
    return f"{komunikat} [{podpowiedz}]" if podpowiedz else komunikat


def wczytaj_kwote(komunikat: str = "Kwota", domyslna: Decimal | None = None) -> Decimal:
    """Wczytuje dodatnią kwotę."""
    podpowiedz = formatuj_kwote(domyslna) if domyslna is not None else ""
    return wczytaj(_z_podpowiedzia(komunikat, podpowiedz), parsuj_kwote, domyslna)


def wczytaj_kurs(komunikat: str = "Kurs") -> Decimal:
    """Wczytuje kurs waluty."""
    return wczytaj(komunikat, parsuj_kurs)


def wczytaj_saldo(komunikat: str = "Saldo początkowe") -> Decimal:
    """Wczytuje kwotę, która może być też zerem lub liczbą ujemną."""
    return wczytaj(
        f"{komunikat} [0]",
        lambda tekst: parsuj_kwote(tekst, minimum=None),
        domyslna=Decimal("0.00"),
    )


def wczytaj_date(komunikat: str = "Data", domyslna: date | None = None) -> date:
    """Wczytuje datę nie późniejszą niż dzisiejsza (Enter = domyślna albo dziś)."""
    dzis = date.today()
    domyslna = domyslna or dzis
    return wczytaj(
        _z_podpowiedzia(komunikat, formatuj_date(domyslna)),
        lambda tekst: parsuj_date(tekst, najpozniej=dzis),
        domyslna,
    )


def wczytaj_termin(komunikat: str, najwczesniej: date, domyslna: date | None = None) -> date:
    """Wczytuje datę nie wcześniejszą niż podana."""
    return wczytaj(
        _z_podpowiedzia(komunikat, formatuj_date(domyslna) if domyslna else ""),
        lambda tekst: parsuj_date(tekst, najwczesniej=najwczesniej),
        domyslna,
    )


def wczytaj_date_opcjonalna(komunikat: str) -> date | None:
    """Wczytuje datę albo None, gdy użytkownik naciśnie sam Enter."""
    return wczytaj(
        _z_podpowiedzia(komunikat, "bez limitu"),
        lambda tekst: parsuj_date(tekst) if tekst.strip() else None,
    )


def wczytaj_nazwe(komunikat: str, sprawdz: Callable[[str], None]) -> str:
    """Wczytuje krótką nazwę i sprawdza ją dodatkową funkcją."""

    def parser(tekst: str) -> str:
        nazwa = sprawdz_tekst(tekst, komunikat, MAKS_DLUGOSC_NAZWY)
        sprawdz(nazwa)
        return nazwa

    return wczytaj(komunikat, parser)


def wczytaj_sciezke(komunikat: str, domyslna: Path | None = None) -> Path:
    """Wczytuje ścieżkę do pliku, także wklejoną w cudzysłowie."""

    def parser(tekst: str) -> Path:
        bez_cudzyslowu = tekst.strip().strip('"')
        return Path(sprawdz_tekst(bez_cudzyslowu, komunikat, MAKS_DLUGOSC_SCIEZKI))

    return wczytaj(_z_podpowiedzia(komunikat, str(domyslna or "")), parser, domyslna)


def wczytaj_fraze(komunikat: str) -> str:
    """Wczytuje tekst, który może być pusty."""
    return wczytaj(
        _z_podpowiedzia(komunikat, "dowolny"),
        lambda tekst: sprawdz_tekst(tekst, komunikat, puste_ok=True),
    )


def wczytaj_miesiac(komunikat: str = "Miesiąc") -> date:
    """Wczytuje miesiąc (Enter = bieżący)."""
    biezacy = date.today().replace(day=1)
    return wczytaj(f"{komunikat} [{biezacy:%m.%Y}]", parsuj_miesiac, domyslna=biezacy)


def wczytaj_tekst(
    komunikat: str, maks: int = MAKS_DLUGOSC_OPISU, domyslna: str | None = None
) -> str:
    """Wczytuje niepusty tekst."""
    return wczytaj(
        _z_podpowiedzia(komunikat, domyslna or ""),
        lambda tekst: sprawdz_tekst(tekst, komunikat, maks),
        domyslna,
    )


def wczytaj_numer(komunikat: str) -> int:
    """Wczytuje dodatnią liczbę całkowitą."""
    return wczytaj(komunikat, parsuj_numer)


def wczytaj_liczbe(komunikat: str, maks: int, domyslna: int, minimum: int = 0) -> int:
    """Wczytuje liczbę całkowitą z podanego zakresu."""
    return wczytaj(
        _z_podpowiedzia(komunikat, str(domyslna)),
        lambda tekst: parsuj_liczbe(tekst, maks, minimum),
        domyslna,
    )


def wczytaj_wybor(
    komunikat: str, dozwolone: tuple[str, ...], domyslna: str | None = None
) -> str:
    """Wczytuje jedną z dozwolonych opcji."""
    return wczytaj(
        _z_podpowiedzia(komunikat, domyslna or ""),
        lambda tekst: parsuj_wybor(tekst, dozwolone),
        domyslna,
    )


def wybierz(komunikat: str, elementy: list[Any], domyslny: Any = None) -> Any:
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
    numer_domyslny = str(elementy.index(domyslny) + 1) if domyslny in elementy else None
    return elementy[int(wczytaj_wybor(komunikat, numery, numer_domyslny)) - 1]


def wybierz_lub_wszystkie(komunikat: str, elementy: list[Any]) -> Any:
    """Działa jak wybierz(), ale 0 albo Enter oznacza brak wyboru, czyli None."""
    for numer, element in enumerate(("wszystkie", *elementy)):
        print(f"  {numer}) {element}")
    numery = tuple(str(numer) for numer in range(len(elementy) + 1))
    wybor = int(wczytaj_wybor(komunikat, numery, domyslna="0"))
    return None if wybor == 0 else elementy[wybor - 1]


def potwierdz(pytanie: str) -> bool:
    """Zadaje pytanie tak/nie."""
    return wczytaj(f"{pytanie} (t/n)", parsuj_tak_nie)
