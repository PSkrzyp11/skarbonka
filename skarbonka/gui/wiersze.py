"""Zamiana transakcji na wiersze tabeli."""

from skarbonka.gui import styl
from skarbonka.gui.skladniki import Kolumna, Wiersz
from skarbonka.models.transakcja import Przelew, Przychod, Transakcja
from skarbonka.services.zestaw import Serwisy
from skarbonka.utils.formatowanie import formatuj_date, formatuj_kwote

KOLUMNY_TRANSAKCJI = [
    Kolumna("Data", 100),
    Kolumna("Opis", 260, rozciagliwa=True),
    Kolumna("Konto", 170),
    Kolumna("Kategoria", 140),
    Kolumna("Kwota", 140, do_prawej=True),
]

KOLORY = {Przychod.RODZAJ: styl.DOBRY, Przelew.RODZAJ: styl.TEKST_DRUGI}


def wiersze_transakcji(transakcje: list[Transakcja], serwisy: Serwisy) -> list[Wiersz]:
    """Zwraca wiersze z nazwami kont i kategorii.

    Transakcje bez numeru, np. z podglądu importu, dostają numer kolejny.
    """
    konta = serwisy.konta.nazwy()
    kategorie = serwisy.kategorie.nazwy()
    wynik = []
    for numer, t in enumerate(transakcje, start=1):
        konto = konta[t.konto_id]
        if isinstance(t, Przelew):
            konto = f"{konto} → {konta[t.konto_docelowe_id]}"
        kategoria = kategorie.get(t.kategoria_id, "przelew")
        wynik.append(
            Wiersz(
                t.id or numer,
                (
                    formatuj_date(t.data),
                    t.opis_z_waluta,
                    konto,
                    kategoria,
                    t.ZNAK + formatuj_kwote(t.kwota),
                ),
                (t.data, t.opis.casefold(), konto, kategoria, t.wplyw or t.kwota),
                KOLORY.get(t.RODZAJ),
            )
        )
    return wynik
