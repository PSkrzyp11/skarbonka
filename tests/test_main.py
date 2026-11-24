"""Testy opcji uruchomienia."""

import pytest

from main import wczytaj_argumenty


def test_wartosci_domyslne():
    opcje = wczytaj_argumenty([])
    assert opcje.bez_kolorow is False
    assert opcje.debug is False


def test_wlaczone_opcje():
    opcje = wczytaj_argumenty(["--bez-kolorow", "--debug"])
    assert opcje.bez_kolorow and opcje.debug


@pytest.mark.parametrize(("argument", "kod"), [("--wersja", 0), ("--pomoc", 0), ("--brak", 2)])
def test_konczace_opcje(argument, kod):
    with pytest.raises(SystemExit) as wyjscie:
        wczytaj_argumenty([argument])
    assert wyjscie.value.code == kod
