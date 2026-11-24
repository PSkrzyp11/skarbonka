"""Testy raportu tekstowego i pulpitu."""

from datetime import date
from decimal import Decimal

import pytest

from skarbonka.models.cykliczna import Cykliczna
from skarbonka.models.enums import Czestotliwosc
from skarbonka.ui.aplikacja import Aplikacja
from skarbonka.wyjatki import BladPliku

LISTOPAD = date(2026, 11, 1)


def test_tresc_raportu(serwisy, tmp_path):
    serwisy.budzety.ustaw(1, LISTOPAD, Decimal("50"))
    cel = serwisy.cele.dodaj("Wakacje", Decimal("1000"), date(2027, 5, 1))
    serwisy.cele.wplac(cel, Decimal("250"))
    sciezka = tmp_path / "raporty" / "listopad.txt"
    serwisy.raporty.zapisz(LISTOPAD, sciezka)
    tekst = sciezka.read_text(encoding="utf-8")
    for fragment in (
        "raport za listopad 2026",
        "4 600,00 zł",
        "Zaoszczędzono 92,0% przychodów.",
        "75,0%",
        "przekroczony",
        "05.11.2026 Czynsz",
        "25,0%",
        "4 630,00 zł",
    ):
        assert fragment in tekst
    assert "Kawa czarna" not in tekst


def test_pusty_miesiac(serwisy):
    linie = list(serwisy.raporty.linie(date(2020, 1, 1)))
    assert linie[0].endswith("styczeń 2020")
    assert not any("Zaoszczędzono" in linia for linia in linie)
    assert linie.count("brak") == 4


def test_nie_mozna_zapisac(serwisy, tmp_path):
    with pytest.raises(BladPliku):
        serwisy.raporty.zapisz(LISTOPAD, tmp_path)


def test_pulpit(serwisy, capsys):
    aplikacja = Aplikacja(serwisy)
    aplikacja.pokaz_pulpit(date(2026, 11, 24))
    czysty = capsys.readouterr().out
    assert "4 630,00 zł" in czysty
    assert "!" not in czysty

    serwisy.budzety.ustaw(1, LISTOPAD, Decimal("50"))
    serwisy.cele.dodaj("Wakacje", Decimal("1000"), date(2026, 11, 1))
    serwisy.cykliczne.dodaj(
        Cykliczna(
            "Czynsz",
            "wydatek",
            Decimal("1"),
            1,
            2,
            date(2026, 11, 1),
            Czestotliwosc.TYDZIEN,
        ),
        date(2026, 11, 24),
    )
    aplikacja.pokaz_pulpit(date(2026, 11, 24))
    wyjscie = capsys.readouterr().out
    assert "Budżet Jedzenie: przekroczony, wykorzystano 200,0%." in wyjscie
    assert "Zaległe transakcje cykliczne: 4" in wyjscie
    assert "Minął termin celu Wakacje." in wyjscie
