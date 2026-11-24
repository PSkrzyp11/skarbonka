"""Testy budżetów i ustawień."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from skarbonka.models.enums import StanBudzetu
from skarbonka.models.plan import Budzet
from skarbonka.services.ustawienia import SerwisUstawien, Ustawienia
from skarbonka.wyjatki import NieprawidlowaKwota, RekordWUzyciu

LISTOPAD = date(2026, 11, 1)


@pytest.mark.parametrize(
    ("wydano", "stan"),
    [
        ("0", StanBudzetu.W_NORMIE),
        ("79.99", StanBudzetu.W_NORMIE),
        ("80", StanBudzetu.UWAGA),
        ("100", StanBudzetu.UWAGA),
        ("100.01", StanBudzetu.PRZEKROCZONY),
    ],
)
def test_stan_budzetu(wydano, stan):
    assert Budzet(1, LISTOPAD, Decimal("100")).stan(Decimal(wydano)) is stan


def test_limit_musi_byc_dodatni():
    with pytest.raises(NieprawidlowaKwota):
        Budzet(1, LISTOPAD, Decimal("0"))


def test_wykonanie_budzetow(serwisy):
    serwisy.budzety.ustaw(1, date(2026, 11, 15), Decimal("125"))
    serwisy.budzety.ustaw(2, LISTOPAD, Decimal("200"))
    wynik = [(w.kategoria, w.wydano, w.procent, w.stan) for w in serwisy.budzety.wykonanie(LISTOPAD)]
    assert wynik == [
        ("Mieszkanie", Decimal("300.00"), 150.0, StanBudzetu.PRZEKROCZONY),
        ("Jedzenie", Decimal("100.00"), 80.0, StanBudzetu.UWAGA),
    ]
    assert serwisy.budzety.wykonanie(date(2026, 12, 1)) == []


def test_ponowne_ustawienie_zmienia_limit(serwisy):
    serwisy.budzety.ustaw(1, LISTOPAD, Decimal("100"))
    serwisy.budzety.ustaw(1, LISTOPAD, Decimal("500"))
    assert [b.limit for b in serwisy.budzety.z_miesiaca(LISTOPAD)] == [Decimal("500.00")]
    assert serwisy.budzety.ostrzezenia(LISTOPAD) == []


def test_kopiowanie_z_poprzedniego_miesiaca(serwisy):
    serwisy.budzety.ustaw(1, LISTOPAD, Decimal("100"))
    serwisy.budzety.ustaw(2, LISTOPAD, Decimal("200"))
    grudzien = date(2026, 12, 5)
    serwisy.budzety.ustaw(1, grudzien, Decimal("999"))
    assert serwisy.budzety.skopiuj_poprzedni(grudzien) == 1
    assert {b.kategoria_id: b.limit for b in serwisy.budzety.z_miesiaca(grudzien)} == {
        1: Decimal("999.00"),
        2: Decimal("200.00"),
    }


def test_nie_mozna_usunac_kategorii_z_budzetem(serwisy, kategorie):
    budzet = serwisy.budzety.ustaw(4, LISTOPAD, Decimal("100"))
    with pytest.raises(RekordWUzyciu):
        serwisy.kategorie.usun(kategorie[3])
    serwisy.budzety.usun(budzet)
    serwisy.kategorie.usun(kategorie[3])


def test_prog_z_ustawien(serwisy):
    serwisy.budzety.ustaw(1, LISTOPAD, Decimal("200"))
    assert serwisy.budzety.ostrzezenia(LISTOPAD) == []
    serwisy.ustawienia.zapisz(replace(Ustawienia(), prog_ostrzezen=50))
    assert len(serwisy.budzety.ostrzezenia(LISTOPAD)) == 1


@pytest.mark.parametrize("tresc", ["{", "[]", "5", '{"obce": 1}', '{"prog_ostrzezen": "dużo"}'])
def test_bledne_ustawienia_daja_domyslne(tmp_path, tresc):
    plik = tmp_path / "ustawienia.json"
    plik.write_text(tresc, encoding="utf-8")
    assert SerwisUstawien(plik).wczytaj() == Ustawienia()
