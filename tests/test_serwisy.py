"""Testy filtrów, sald, kategorii i analiz."""

from datetime import date
from decimal import Decimal

import pytest

from skarbonka.models.konto import Konto
from skarbonka.models.enums import TypKonta
from skarbonka.models.transakcja import Przelew, Przychod, Wydatek
from skarbonka.services import analizy, rekordy
from skarbonka.services.kategorie import domyslne_kategorie, pasujace, usun_kategorie
from skarbonka.services.konta import saldo, usun_konto
from skarbonka.services.transakcje import bilans, filtruj, posortuj, suma_wydatkow
from skarbonka.wyjatki import BladWalidacji, NieZnalezionoRekordu, RekordWUzyciu

LISTOPAD = date(2026, 11, 1)


def numery(transakcje):
    return [t.id for t in transakcje]


def test_dodawanie_nadaje_kolejne_numery(konta):
    nowe = Konto("Nowe", TypKonta.GOTOWKA)
    rekordy.dodaj(konta, nowe)
    assert nowe.id == 4


def test_zmiana_i_usuwanie(konta):
    rekordy.zmien(konta, Konto("Zmienione", TypKonta.GOTOWKA, id=2))
    assert rekordy.znajdz(konta, 2).nazwa == "Zmienione"
    rekordy.usun(konta, 2)
    with pytest.raises(NieZnalezionoRekordu):
        rekordy.znajdz(konta, 2)


def test_nazwa_musi_byc_unikalna(konta):
    with pytest.raises(BladWalidacji):
        rekordy.sprawdz_nazwe(konta, "PORTFEL")


def test_filtr_bez_warunkow_zwraca_wszystko(transakcje):
    assert filtruj(transakcje) == transakcje


@pytest.mark.parametrize(
    ("warunki", "oczekiwane"),
    [
        ({"od": LISTOPAD}, [2, 3, 4, 5]),
        ({"do": date(2026, 11, 1)}, [1, 2]),
        ({"konto_id": 1}, [1, 4, 5]),
        ({"kategoria_id": 1}, [1, 4]),
        ({"fraza": "kawa"}, [1, 4]),
        ({"od": LISTOPAD, "fraza": "kawa", "konto_id": 1}, [4]),
        ({"fraza": "brak takiej"}, []),
    ],
)
def test_filtry(transakcje, warunki, oczekiwane):
    assert numery(filtruj(transakcje, **warunki)) == oczekiwane


def test_filtr_z_odwrocona_kolejnoscia_dat(transakcje):
    with pytest.raises(BladWalidacji):
        filtruj(transakcje, od=date(2026, 12, 1), do=LISTOPAD)


def test_sortowanie(transakcje):
    assert numery(posortuj(transakcje)) == [5, 4, 3, 2, 1]
    assert numery(posortuj(transakcje, "od największych kwot")) == [2, 5, 3, 4, 1]


def test_sumy_pomijaja_przelewy(transakcje):
    assert suma_wydatkow(transakcje) == Decimal("420.00")
    assert bilans(transakcje) == Decimal("4580.00")
    assert bilans([]) == 0


def test_salda_kont(konta, transakcje):
    assert saldo(konta, transakcje, 1) == Decimal("980.00")
    assert saldo(konta, transakcje, 2) == Decimal("3650.00")
    assert saldo(konta, transakcje) == Decimal("4630.00")


def test_usuwanie_konta(konta, transakcje):
    with pytest.raises(RekordWUzyciu):
        usun_konto(konta, konta[0], transakcje)
    usun_konto(konta, konta[2], transakcje)
    assert len(konta) == 2


def test_kategorie_dla_rodzaju(kategorie):
    assert [k.nazwa for k in pasujace(kategorie, Przychod)] == ["Wynagrodzenie"]
    assert len(pasujace(kategorie, Wydatek)) == 3
    assert pasujace(kategorie, Przelew) == []


def test_domyslne_kategorie_maja_unikalne_numery():
    kategorie = domyslne_kategorie()
    assert len({k.id for k in kategorie}) == len(kategorie)


def test_usuwanie_kategorii(kategorie, transakcje):
    with pytest.raises(RekordWUzyciu):
        usun_kategorie(kategorie, kategorie[0], transakcje)
    usun_kategorie(kategorie, kategorie[3], transakcje)
    assert len(kategorie) == 3


def test_podsumowanie_miesiaca(transakcje):
    assert analizy.podsumowanie_miesiaca(transakcje, date(2026, 11, 30)) == {
        "Przychody": Decimal("5000.00"),
        "Wydatki": Decimal("400.00"),
        "Bilans": Decimal("4600.00"),
    }


def test_stopa_oszczednosci():
    assert analizy.stopa_oszczednosci(Decimal("200"), Decimal("50")) == 25.0
    assert analizy.stopa_oszczednosci(Decimal("0"), Decimal("-10")) is None


def test_wydatki_wg_kategorii(transakcje, kategorie):
    wynik = analizy.wydatki_wg_kategorii(transakcje, kategorie)
    assert list(wynik.items()) == [
        ("Mieszkanie", Decimal("300.00")),
        ("Jedzenie", Decimal("120.00")),
    ]


def test_udzialy():
    assert analizy.udzialy({"a": Decimal("75"), "b": Decimal("25")}) == {"a": 75.0, "b": 25.0}
    assert analizy.udzialy({}) == {}


def test_trend_obejmuje_przelom_roku(transakcje):
    wynik = analizy.trend(transakcje, ostatni=date(2027, 1, 15), ile=4)
    assert [m for m, _ in wynik] == [
        date(2026, 10, 1),
        date(2026, 11, 1),
        date(2026, 12, 1),
        date(2027, 1, 1),
    ]
    assert wynik[1][1]["Wydatki"] == Decimal("400.00")


def test_najwieksze_wydatki(transakcje):
    assert numery(analizy.najwieksze_wydatki(transakcje, ile=2)) == [3, 4]
    assert len(analizy.najwieksze_wydatki(transakcje)) == 3
