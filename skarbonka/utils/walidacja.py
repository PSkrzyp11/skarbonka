"""Zamiana tekstu od użytkownika na poprawne wartości.

Każda funkcja zwraca gotową wartość albo zgłasza wyjątek z rodziny
BladWalidacji. Nic tu nie jest wypisywane na ekran.
"""

import re
from datetime import date, datetime, timedelta
from decimal import Decimal

from skarbonka.config import MAKS_DLUGOSC_OPISU
from skarbonka.wyjatki import BladWalidacji, NieprawidlowaData, NieprawidlowaKwota

MIN_KWOTA = Decimal("0.01")
MAKS_KWOTA = Decimal("999999999.99")

WZORZEC_KWOTY = re.compile(r"[+-]?([0-9]+|[0-9]{1,3}( [0-9]{3})+)([.,][0-9]{1,2})?")

FORMATY_DATY = ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y")
MIN_DATA = date(2000, 1, 1)
MAKS_DATA = date(2100, 12, 31)


def parsuj_kwote(tekst: str, minimum: Decimal | None = MIN_KWOTA) -> Decimal:
    """Zamienia tekst na kwotę w złotych.

    minimum=None wyłącza dolny limit (np. ujemne saldo początkowe konta).
    """
    czysty = tekst.strip().lower()
    for jednostka in ("pln", "zł"):
        czysty = czysty.removesuffix(jednostka).rstrip()
    czysty = czysty.replace(" ", " ").replace(" ", " ").replace("−", "-")

    if not czysty:
        raise NieprawidlowaKwota("Kwota nie może być pusta.")
    if not WZORZEC_KWOTY.fullmatch(czysty):
        raise NieprawidlowaKwota(
            f"„{tekst.strip()}” nie jest kwotą. Przykłady: 45 | 45,90 | 1 234,50."
        )

    kwota = Decimal(czysty.replace(" ", "").replace(",", "."))
    if minimum is not None and kwota < minimum:
        opis_minimum = str(minimum).replace(".", ",")
        raise NieprawidlowaKwota(f"Kwota musi wynosić co najmniej {opis_minimum} zł.")
    if abs(kwota) > MAKS_KWOTA:
        raise NieprawidlowaKwota("Kwota jest zbyt duża.")
    return kwota


def parsuj_date(
    tekst: str,
    domyslna: date | None = None,
    najpozniej: date | None = None,
) -> date:
    """Zamienia tekst na datę.

    Rozumie kilka formatów oraz słowa „dziś” i „wczoraj”. Pusty tekst oznacza
    datę domyślną, o ile została podana.
    """
    czysty = tekst.strip().lower()
    if not czysty:
        if domyslna is None:
            raise NieprawidlowaData("Data nie może być pusta.")
        wynik = domyslna
    elif czysty in ("dziś", "dzis", "dzisiaj"):
        wynik = date.today()
    elif czysty == "wczoraj":
        wynik = date.today() - timedelta(days=1)
    else:
        wynik = _dopasuj_format(czysty)

    if not MIN_DATA <= wynik <= MAKS_DATA:
        raise NieprawidlowaData(
            f"Data musi być między {MIN_DATA:%d.%m.%Y} a {MAKS_DATA:%d.%m.%Y}."
        )
    if najpozniej is not None and wynik > najpozniej:
        raise NieprawidlowaData(f"Data nie może być późniejsza niż {najpozniej:%d.%m.%Y}.")
    return wynik


def _dopasuj_format(tekst: str) -> date:
    """Próbuje kolejnych formatów daty, aż któryś zadziała."""
    for wzor in FORMATY_DATY:
        try:
            return datetime.strptime(tekst, wzor).date()
        except ValueError:
            continue
    raise NieprawidlowaData(
        f"„{tekst}” nie jest poprawną datą. Przykłady: 24.11.2026 | 2026-11-24 | dziś."
    )


def sprawdz_tekst(
    tekst: str,
    nazwa: str = "Tekst",
    maks: int = MAKS_DLUGOSC_OPISU,
    puste_ok: bool = False,
) -> str:
    """Zwraca tekst bez zbędnych spacji albo zgłasza BladWalidacji."""
    czysty = " ".join(tekst.split())
    if not czysty and not puste_ok:
        raise BladWalidacji(f"{nazwa} – pole nie może być puste.")
    if len(czysty) > maks:
        raise BladWalidacji(f"{nazwa} – maksymalnie {maks} znaków, a jest {len(czysty)}.")
    if not czysty.isprintable():
        raise BladWalidacji(f"{nazwa} – pole zawiera niedozwolone znaki.")
    return czysty


def parsuj_tak_nie(tekst: str) -> bool:
    """Zamienia odpowiedź tak/nie na wartość logiczną."""
    czysty = tekst.strip().lower()
    if czysty in ("t", "tak"):
        return True
    if czysty in ("n", "nie"):
        return False
    raise BladWalidacji("Wpisz „t” (tak) albo „n” (nie).")


def parsuj_wybor(tekst: str, dozwolone: tuple[str, ...]) -> str:
    """Sprawdza, czy tekst jest jedną z dozwolonych opcji."""
    czysty = tekst.strip().lower()
    if czysty not in dozwolone:
        raise BladWalidacji(f"Dostępne opcje: {', '.join(dozwolone)}.")
    return czysty
