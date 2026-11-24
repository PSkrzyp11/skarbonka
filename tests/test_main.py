"""Testy opcji uruchomienia."""

import pytest

from main import main, wczytaj_argumenty


def test_wartosci_domyslne():
    opcje = wczytaj_argumenty([])
    assert opcje.bez_kolorow is False
    assert opcje.debug is False
    assert opcje.baza.name == "skarbonka.db"


def test_wlaczone_opcje():
    opcje = wczytaj_argumenty(["--bez-kolorow", "--debug"])
    assert opcje.bez_kolorow and opcje.debug


@pytest.mark.parametrize(("argument", "kod"), [("--wersja", 0), ("--pomoc", 0), ("--brak", 2)])
def test_konczace_opcje(argument, kod):
    with pytest.raises(SystemExit) as wyjscie:
        wczytaj_argumenty([argument])
    assert wyjscie.value.code == kod


def test_dane_przezywaja_ponowne_uruchomienie(tmp_path, monkeypatch, odpowiedzi, capsys):
    monkeypatch.setattr("main.skonfiguruj_logi", lambda **opcje: True)
    argumenty = ["--baza", str(tmp_path / "test.db")]
    odpowiedzi("1", "1", "20", "", "Kawa", "1", "0", "0")
    main(argumenty)
    odpowiedzi("1", "5", "0", "0")
    main(argumenty)
    assert "Pokazano 1 z 1" in capsys.readouterr().out


def test_nie_da_sie_otworzyc_bazy(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("main.skonfiguruj_logi", lambda **opcje: False)
    main(["--baza", str(tmp_path)])
    wyjscie = capsys.readouterr().out
    assert "bez logowania" in wyjscie
    assert "Nie można otworzyć bazy" in wyjscie
