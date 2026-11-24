"""Zamiana transakcji na pozycje listy."""

from itertools import groupby

from skarbonka.gui import ikony, styl
from skarbonka.gui.lista import Naglowek, Pozycja
from skarbonka.models.transakcja import Przelew, Przychod, Transakcja
from skarbonka.services.transakcje import bilans
from skarbonka.services.zestaw import Serwisy
from skarbonka.utils.formatowanie import formatuj_date, formatuj_dzien, formatuj_kwote

KOLORY = {Przychod.RODZAJ: styl.DOBRY, Przelew.RODZAJ: styl.TEKST_DRUGI}
MINUS = "−"


def kwota_ze_znakiem(tekst: str) -> str:
    """Zamienia zwykły myślnik na znak minus o szerokości cyfry."""
    return tekst.replace("-", MINUS)


def pozycje_transakcji(
    transakcje: list[Transakcja], serwisy: Serwisy, z_data: bool = False
) -> list[Pozycja]:
    """Zwraca pozycje z ikoną kategorii.

    Transakcje bez numeru, np. z podglądu importu, dostają numer kolejny.
    """
    konta = serwisy.konta.nazwy()
    kategorie = serwisy.kategorie.nazwy()
    wynik = []
    for numer, t in enumerate(transakcje, start=1):
        if isinstance(t, Przelew):
            ikona, opis = ikony.STRZALKI, f"{konta[t.konto_id]} → {konta[t.konto_docelowe_id]}"
        else:
            kategoria = kategorie.get(t.kategoria_id, "")
            ikona, opis = ikony.dla_nazwy(kategoria), f"{kategoria}  ·  {konta[t.konto_id]}"
        podpisy = [formatuj_date(t.data)] if z_data else []
        if t.kwota_oryg is not None:
            podpisy.append(formatuj_kwote(t.kwota_oryg, jednostka=t.waluta))
        wynik.append(
            Pozycja(
                t.id or numer,
                ikona,
                t.opis,
                opis,
                kwota_ze_znakiem(t.ZNAK + formatuj_kwote(t.kwota)),
                "  ·  ".join(podpisy),
                KOLORY.get(t.RODZAJ, styl.TEKST),
                wyrozniona=isinstance(t, Przychod),
            )
        )
    return wynik


def pogrupowane_dniami(transakcje: list[Transakcja], serwisy: Serwisy) -> list[Pozycja | Naglowek]:
    """Zwraca pozycje z nagłówkiem każdego dnia i jego bilansem."""
    wynik: list[Pozycja | Naglowek] = []
    for dzien, grupa in groupby(transakcje, key=lambda t: t.data):
        z_dnia = list(grupa)
        suma = kwota_ze_znakiem(formatuj_kwote(bilans(z_dnia)))
        wynik.append(Naglowek(formatuj_dzien(dzien), suma))
        wynik.extend(pozycje_transakcji(z_dnia, serwisy))
    return wynik
