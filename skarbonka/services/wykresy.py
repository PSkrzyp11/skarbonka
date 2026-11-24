"""Wykresy do zapisania w PNG albo do pokazania w oknie.

Biblioteka matplotlib wydłuża start programu, a bywa potrzebna rzadko. Dlatego
jest importowana dopiero przy pierwszym wykresie.
"""

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

from skarbonka.utils.formatowanie import formatuj_kwote, formatuj_miesiac
from skarbonka.wyjatki import BladPliku, BrakBiblioteki

if TYPE_CHECKING:
    from matplotlib.figure import Figure

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Paleta:
    """Kolory wykresu dopasowane do tła."""

    tlo: str
    tekst: str
    tekst_drugi: str
    siatka: str
    pierwszy: str
    drugi: str


JASNA = Paleta("#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6", "#eb6834")
CIEMNA = Paleta("#1f1f1e", "#f0efec", "#c3c2b7", "#3a3935", "#3987e5", "#d95926")

ROZMIAR = (9, 5)
GRUBOSC_SLUPKA = 0.36
GRUBOSC_KOLUMNY = 0.22
MARGINES = 0.2
ROZDZIELCZOSC = 130


def rysuj_kategorie(
    kwoty: dict[str, Decimal], tytul: str = "", paleta: Paleta = JASNA
) -> "Figure":
    """Rysuje poziome słupki: wydatki w kategoriach, największe na górze."""
    rysunek, osie = _nowy_rysunek(tytul, paleta)
    nazwy = list(kwoty)[::-1]
    wartosci = [float(kwota) for kwota in kwoty.values()][::-1]
    osie.barh(nazwy, wartosci, height=GRUBOSC_SLUPKA, color=paleta.pierwszy)
    for polozenie, nazwa in enumerate(nazwy):
        osie.annotate(
            formatuj_kwote(kwoty[nazwa]),
            (wartosci[polozenie], polozenie),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            color=paleta.tekst,
        )
    osie.set_xlim(0, max(wartosci) * 1.25)
    osie.xaxis.set_visible(False)
    return rysunek


def rysuj_trend(
    wiersze: list[tuple[date, dict[str, Decimal]]], tytul: str = "", paleta: Paleta = JASNA
) -> "Figure":
    """Rysuje pary słupków: przychody i wydatki w kolejnych miesiącach."""
    rysunek, osie = _nowy_rysunek(tytul, paleta)
    miesiace, sumy = zip(*wiersze)
    przesuniecie = GRUBOSC_KOLUMNY / 2 + 0.01
    serie = (
        ("Przychody", paleta.pierwszy, -przesuniecie),
        ("Wydatki", paleta.drugi, przesuniecie),
    )
    for nazwa, kolor, odstep in serie:
        osie.bar(
            [i + odstep for i in range(len(miesiace))],
            [float(suma[nazwa]) for suma in sumy],
            width=GRUBOSC_KOLUMNY,
            color=kolor,
            label=nazwa,
        )
    osie.set_xticks(range(len(miesiace)), [f"{m:%m.%Y}" for m in miesiace])
    osie.legend(frameon=False, labelcolor=paleta.tekst, loc="upper left", ncols=2)
    _os_kwot(osie, paleta, rezerwa=1.2)
    return rysunek


def rysuj_saldo(
    historia: list[tuple[date, Decimal]], tytul: str = "", paleta: Paleta = JASNA
) -> "Figure":
    """Rysuje linię łącznego salda i podpisuje ostatnią wartość."""
    rysunek, osie = _nowy_rysunek(tytul, paleta)
    daty, salda = zip(*historia)
    wartosci = [float(saldo) for saldo in salda]
    osie.plot(daty, wartosci, color=paleta.pierwszy, linewidth=2, solid_capstyle="round")
    styl_punktu = {"markersize": 9, "markeredgecolor": paleta.tlo, "markeredgewidth": 2}
    osie.plot(daty[-1], wartosci[-1], "o", color=paleta.pierwszy, **styl_punktu)
    osie.annotate(
        formatuj_kwote(salda[-1]),
        (daty[-1], wartosci[-1]),
        xytext=(10, 0),
        textcoords="offset points",
        va="center",
        color=paleta.tekst,
    )
    osie.axhline(0, color=paleta.tekst_drugi, linewidth=1)
    podzialka = daty[:: max(1, len(daty) // 4)]
    osie.set_xticks(podzialka, [f"{d:%d.%m}" for d in podzialka])
    _os_kwot(osie, paleta, rezerwa=1.1)
    return rysunek


def tytul_kategorii(miesiac: date) -> str:
    """Zwraca tytuł wykresu kategorii."""
    return f"Wydatki według kategorii, {formatuj_miesiac(miesiac)}"


def zapisz(rysunek: "Figure", sciezka: Path) -> None:
    """Zapisuje rysunek do pliku PNG."""
    try:
        sciezka.parent.mkdir(parents=True, exist_ok=True)
        rysunek.savefig(sciezka, dpi=ROZDZIELCZOSC, facecolor=rysunek.get_facecolor())
    except (OSError, ValueError) as blad:
        raise BladPliku(f"Nie można zapisać wykresu {sciezka}: {blad}") from blad
    logger.info("Zapisano wykres %s", sciezka.name)


def _nowy_rysunek(tytul: str, paleta: Paleta) -> tuple["Figure", Any]:
    """Tworzy pusty rysunek w jednym, wspólnym stylu."""
    try:
        from matplotlib.figure import Figure
    except ImportError as blad:
        raise BrakBiblioteki("Wykresy wymagają biblioteki matplotlib.") from blad

    rysunek = Figure(figsize=ROZMIAR, facecolor=paleta.tlo, layout="constrained")
    rysunek.get_layout_engine().set(w_pad=MARGINES, h_pad=MARGINES)
    osie = rysunek.subplots()
    osie.set_facecolor(paleta.tlo)
    if tytul:
        osie.set_title(tytul, loc="left", color=paleta.tekst, fontsize=14, pad=14)
    osie.tick_params(colors=paleta.tekst_drugi, length=0, labelsize=9)
    for strona in ("top", "right", "left", "bottom"):
        osie.spines[strona].set_visible(False)
    return rysunek, osie


def _os_kwot(osie: Any, paleta: Paleta, rezerwa: float = 1.0) -> None:
    """Dodaje siatkę i pełne kwoty na osi pionowej."""
    dol, gora = osie.get_ylim()
    osie.set_ylim(dol, gora * rezerwa if gora > 0 else gora)
    osie.set_axisbelow(True)
    osie.grid(axis="y", color=paleta.siatka, linewidth=1)
    osie.yaxis.set_major_formatter(lambda wartosc, _: f"{wartosc:,.0f} zł".replace(",", " "))
