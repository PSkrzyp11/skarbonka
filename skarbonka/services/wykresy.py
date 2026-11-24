"""Wykresy zapisywane do plików PNG.

Biblioteka matplotlib wydłuża start programu, a bywa potrzebna rzadko. Dlatego
jest importowana dopiero przy pierwszym wykresie.
"""

import logging
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

from skarbonka.utils.formatowanie import formatuj_kwote, formatuj_miesiac
from skarbonka.wyjatki import BladPliku, BrakBiblioteki

if TYPE_CHECKING:
    from matplotlib.figure import Figure

logger = logging.getLogger(__name__)

TLO = "#fcfcfb"
TEKST = "#0b0b0b"
TEKST_DRUGI = "#52514e"
SIATKA = "#e4e3df"
NIEBIESKI = "#2a78d6"
POMARANCZOWY = "#eb6834"

ROZMIAR = (9, 5)
GRUBOSC_SLUPKA = 0.36
GRUBOSC_KOLUMNY = 0.22
MARGINES = 0.2
ROZDZIELCZOSC = 130


def wykres_kategorii(kwoty: dict[str, Decimal], miesiac: date, sciezka: Path) -> None:
    """Rysuje poziome słupki: wydatki w kategoriach, największe na górze."""
    rysunek, osie = _nowy_rysunek(f"Wydatki według kategorii, {formatuj_miesiac(miesiac)}")
    nazwy = list(kwoty)[::-1]
    wartosci = [float(kwota) for kwota in kwoty.values()][::-1]
    osie.barh(nazwy, wartosci, height=GRUBOSC_SLUPKA, color=NIEBIESKI)
    for polozenie, nazwa in enumerate(nazwy):
        osie.annotate(
            formatuj_kwote(kwoty[nazwa]),
            (wartosci[polozenie], polozenie),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            color=TEKST,
        )
    osie.set_xlim(0, max(wartosci) * 1.2)
    osie.xaxis.set_visible(False)
    _zapisz(rysunek, sciezka)


def wykres_trendu(wiersze: list[tuple[date, dict[str, Decimal]]], sciezka: Path) -> None:
    """Rysuje pary słupków: przychody i wydatki w kolejnych miesiącach."""
    rysunek, osie = _nowy_rysunek("Przychody i wydatki")
    miesiace, sumy = zip(*wiersze)
    przesuniecie = GRUBOSC_KOLUMNY / 2 + 0.01
    serie = (("Przychody", NIEBIESKI, -przesuniecie), ("Wydatki", POMARANCZOWY, przesuniecie))
    for nazwa, kolor, odstep in serie:
        osie.bar(
            [i + odstep for i in range(len(miesiace))],
            [float(suma[nazwa]) for suma in sumy],
            width=GRUBOSC_KOLUMNY,
            color=kolor,
            label=nazwa,
        )
    osie.set_xticks(range(len(miesiace)), [f"{m:%m.%Y}" for m in miesiace])
    osie.legend(frameon=False, labelcolor=TEKST, loc="upper left", ncols=2)
    _os_kwot(osie, rezerwa=1.2)
    _zapisz(rysunek, sciezka)


def wykres_salda(historia: list[tuple[date, Decimal]], sciezka: Path) -> None:
    """Rysuje linię łącznego salda i podpisuje ostatnią wartość."""
    rysunek, osie = _nowy_rysunek("Łączne saldo kont")
    daty, salda = zip(*historia)
    wartosci = [float(saldo) for saldo in salda]
    osie.plot(daty, wartosci, color=NIEBIESKI, linewidth=2, solid_capstyle="round")
    styl_punktu = {"markersize": 9, "markeredgecolor": TLO, "markeredgewidth": 2}
    osie.plot(daty[-1], wartosci[-1], "o", color=NIEBIESKI, **styl_punktu)
    osie.annotate(
        formatuj_kwote(salda[-1]),
        (daty[-1], wartosci[-1]),
        xytext=(10, 0),
        textcoords="offset points",
        va="center",
        color=TEKST,
    )
    osie.axhline(0, color=TEKST_DRUGI, linewidth=1)
    podzialka = daty[:: max(1, len(daty) // 5)]
    osie.set_xticks(podzialka, [f"{d:%d.%m}" for d in podzialka])
    _os_kwot(osie)
    _zapisz(rysunek, sciezka)


def _nowy_rysunek(tytul: str) -> tuple["Figure", Any]:
    """Tworzy pusty rysunek w jednym, wspólnym stylu."""
    try:
        from matplotlib.figure import Figure
    except ImportError as blad:
        raise BrakBiblioteki("Wykresy wymagają biblioteki matplotlib.") from blad

    rysunek = Figure(figsize=ROZMIAR, facecolor=TLO, layout="constrained")
    rysunek.get_layout_engine().set(w_pad=MARGINES, h_pad=MARGINES)
    osie = rysunek.subplots()
    osie.set_facecolor(TLO)
    osie.set_title(tytul, loc="left", color=TEKST, fontsize=14, pad=14)
    osie.tick_params(colors=TEKST_DRUGI, length=0)
    for strona in ("top", "right", "left", "bottom"):
        osie.spines[strona].set_visible(False)
    return rysunek, osie


def _os_kwot(osie: Any, rezerwa: float = 1.0) -> None:
    """Dodaje siatkę i pełne kwoty na osi pionowej."""
    dol, gora = osie.get_ylim()
    osie.set_ylim(dol, gora * rezerwa)
    osie.set_axisbelow(True)
    osie.grid(axis="y", color=SIATKA, linewidth=1)
    osie.yaxis.set_major_formatter(lambda wartosc, _: f"{wartosc:,.0f} zł".replace(",", " "))


def _zapisz(rysunek: "Figure", sciezka: Path) -> None:
    """Zapisuje rysunek do pliku."""
    try:
        sciezka.parent.mkdir(parents=True, exist_ok=True)
        rysunek.savefig(sciezka, dpi=ROZDZIELCZOSC, facecolor=TLO)
    except (OSError, ValueError) as blad:
        raise BladPliku(f"Nie można zapisać wykresu {sciezka}: {blad}") from blad
    logger.info("Zapisano wykres %s", sciezka.name)
