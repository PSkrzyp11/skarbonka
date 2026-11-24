"""Testy budżetów, celów i ustawień."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from skarbonka.models.enums import StanBudzetu
from skarbonka.models.plan import Budzet, Cel
from skarbonka.services.ustawienia import SerwisUstawien, Ustawienia
from skarbonka.wyjatki import BladWalidacji, NieprawidlowaKwota, RekordWUzyciu

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


@pytest.mark.parametrize(
    ("odlozono", "termin", "rata"),
    [
        ("0", date(2027, 5, 1), "166.67"),
        ("400", date(2027, 5, 1), "100.00"),
        ("0", date(2026, 11, 30), "1000.00"),
        ("0", date(2025, 1, 1), "1000.00"),
        ("1500", date(2027, 5, 1), "0.00"),
    ],
)
def test_rata_celu(odlozono, termin, rata):
    cel = Cel("Wakacje", Decimal("1000"), termin, Decimal(odlozono))
    assert cel.rata(LISTOPAD) == Decimal(rata)


def test_postep_celu(serwisy):
    cel = serwisy.cele.dodaj("Wakacje", Decimal("1000"), date(2027, 5, 1))
    inny = serwisy.cele.dodaj("Rower", Decimal("500"), date(2026, 12, 1))
    for kwota in ("100", "150.50"):
        serwisy.cele.wplac(cel, Decimal(kwota))
    serwisy.cele.wplac(inny, Decimal("600"))
    rower, wakacje = serwisy.cele.wszystkie()
    assert (wakacje.odlozono, wakacje.brakuje) == (Decimal("250.50"), Decimal("749.50"))
    assert wakacje.procent == pytest.approx(25.05)
    assert rower.brakuje == 0


def test_bledne_cele(serwisy):
    cel = serwisy.cele.dodaj("Wakacje", Decimal("1000"), LISTOPAD)
    with pytest.raises(BladWalidacji):
        serwisy.cele.dodaj("WAKACJE", Decimal("1"), LISTOPAD)
    with pytest.raises(NieprawidlowaKwota):
        serwisy.cele.dodaj("Inny", Decimal("0"), LISTOPAD)
    with pytest.raises(NieprawidlowaKwota):
        serwisy.cele.wplac(cel, Decimal("-1"))


def test_usuniecie_celu_usuwa_wplaty(baza, serwisy):
    cel = serwisy.cele.dodaj("Wakacje", Decimal("1000"), LISTOPAD)
    serwisy.cele.wplac(cel, Decimal("10"))
    serwisy.cele.usun(cel)
    assert serwisy.cele.wszystkie() == []
    assert baza.zapytaj("SELECT * FROM wplaty_celu") == []
