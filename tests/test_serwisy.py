"""Testy filtrów, sald, kategorii i analiz."""

from datetime import date
from decimal import Decimal

import pytest

from skarbonka.models.enums import TypKonta
from skarbonka.models.transakcja import Przelew, Przychod, Wydatek
from skarbonka.services import analizy
from skarbonka.services.transakcje import bilans, posortuj, strony, suma_wydatkow
from skarbonka.services.zestaw import dodaj_dane_startowe, utworz_serwisy
from skarbonka.wyjatki import BladWalidacji, RekordWUzyciu

LISTOPAD = date(2026, 11, 1)


def numery(transakcje):
    return [t.id for t in transakcje]


def test_filtr_bez_warunkow_zwraca_wszystko(serwisy, transakcje):
    assert serwisy.transakcje.filtruj() == transakcje


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
def test_filtry(serwisy, warunki, oczekiwane):
    assert numery(serwisy.transakcje.filtruj(**warunki)) == oczekiwane


def test_filtr_z_odwrocona_kolejnoscia_dat(serwisy):
    with pytest.raises(BladWalidacji):
        serwisy.transakcje.filtruj(od=date(2026, 12, 1), do=LISTOPAD)


def test_sortowanie(transakcje):
    assert numery(posortuj(transakcje)) == [5, 4, 3, 2, 1]
    assert numery(posortuj(transakcje, "od największych kwot")) == [2, 5, 3, 4, 1]


def test_strony(transakcje):
    assert [numery(s) for s in strony(transakcje, rozmiar=2)] == [[1, 2], [3, 4], [5]]
    assert list(strony([])) == []


def test_sumy_pomijaja_przelewy(transakcje):
    assert suma_wydatkow(transakcje) == Decimal("420.00")
    assert bilans(transakcje) == Decimal("4580.00")
    assert bilans([]) == 0


def test_salda_kont(serwisy):
    assert serwisy.konta.saldo(1) == Decimal("980.00")
    assert serwisy.konta.saldo(2) == Decimal("3650.00")
    assert serwisy.konta.saldo() == Decimal("4630.00")


def test_nazwa_konta_musi_byc_unikalna(serwisy):
    with pytest.raises(BladWalidacji):
        serwisy.konta.dodaj("PORTFEL", TypKonta.GOTOWKA)


def test_usuwanie_konta(serwisy, konta):
    with pytest.raises(RekordWUzyciu):
        serwisy.konta.usun(konta[0])
    serwisy.konta.usun(konta[2])
    assert serwisy.konta.nazwy() == {1: "Portfel", 2: "ROR"}


def test_kategorie_dla_rodzaju(serwisy):
    assert [k.nazwa for k in serwisy.kategorie.pasujace(Przychod)] == ["Wynagrodzenie"]
    assert len(serwisy.kategorie.pasujace(Wydatek)) == 3
    assert serwisy.kategorie.pasujace(Przelew) == []


def test_usuwanie_kategorii(serwisy, kategorie):
    with pytest.raises(RekordWUzyciu):
        serwisy.kategorie.usun(kategorie[0])
    serwisy.kategorie.usun(kategorie[3])
    assert len(serwisy.kategorie.wszystkie()) == 3


def test_dane_startowe(baza):
    serwisy = utworz_serwisy(baza)
    for _ in range(2):
        dodaj_dane_startowe(serwisy)
    assert list(serwisy.konta.nazwy().values()) == ["Portfel"]
    assert serwisy.kategorie.pasujace(Wydatek)
    assert serwisy.kategorie.pasujace(Przychod)


def test_zmiana_i_usuniecie_transakcji(serwisy, transakcje):
    nowa = Wydatek(LISTOPAD, Decimal("1.00"), "Zmieniona", 1, 1, id=3)
    serwisy.transakcje.zmien(nowa)
    assert serwisy.transakcje.pobierz(3).opis == "Zmieniona"
    serwisy.transakcje.usun(transakcje[0])
    assert numery(serwisy.transakcje.wszystkie()) == [2, 3, 4, 5]


def test_podsumowanie_miesiaca(transakcje):
    assert analizy.podsumowanie_miesiaca(transakcje, date(2026, 11, 30)) == {
        "Przychody": Decimal("5000.00"),
        "Wydatki": Decimal("400.00"),
        "Bilans": Decimal("4600.00"),
    }


def test_stopa_oszczednosci():
    assert analizy.stopa_oszczednosci(Decimal("200"), Decimal("50")) == 25.0
    assert analizy.stopa_oszczednosci(Decimal("0"), Decimal("-10")) is None


def test_opis_oszczednosci():
    przychody = Decimal("200")
    assert "25,0%" in analizy.opis_oszczednosci(przychody, Decimal("50"))
    assert "Wydatki były" in analizy.opis_oszczednosci(przychody, Decimal("-1"))
    assert analizy.opis_oszczednosci(Decimal("0"), Decimal("-1")) == ""


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
