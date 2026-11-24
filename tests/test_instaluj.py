"""Testy instalatora skrótów. Nie dotykają prawdziwego pulpitu."""

import sys

import pytest

import instaluj
from skarbonka.config import KATALOG_PROJEKTU, PLIK_IKONY

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="tylko Windows")


@pytest.fixture
def miejsca(monkeypatch, tmp_path):
    """Przekierowuje skróty i polecenia do katalogu tymczasowego."""
    skroty = [tmp_path / "Pulpit.lnk", tmp_path / "Start.lnk"]
    monkeypatch.setattr(instaluj, "miejsca_skrotow", lambda: skroty)
    monkeypatch.setattr(instaluj, "katalog_polecen", lambda: tmp_path)
    return tmp_path


def test_instalacja_i_usuniecie(miejsca, capsys):
    assert instaluj.main([]) == 0
    assert {plik.name for plik in miejsca.iterdir()} == {
        "Pulpit.lnk",
        "Start.lnk",
        "skarbonka.cmd",
        "skarbonka-konsola.cmd",
    }
    assert "main.py" in (miejsca / "skarbonka.cmd").read_text(encoding="oem")
    assert instaluj.main(["--usun"]) == 0
    assert list(miejsca.iterdir()) == []
    assert instaluj.main(["--usun"]) == 0
    assert capsys.readouterr().out.count("Usunięto") == 4


def test_okno_nie_otwiera_konsoli():
    polecenia = instaluj.tresc_polecen()
    assert "pythonw.exe" in polecenia[instaluj.POLECENIE_OKNA]
    assert "--okno" in polecenia[instaluj.POLECENIE_OKNA]
    assert "--okno" not in polecenia[instaluj.POLECENIE_KONSOLI]


def test_blad_zapisu(miejsca, monkeypatch, capsys):
    monkeypatch.setattr(instaluj, "katalog_polecen", lambda: miejsca / "nie ma takiego")
    assert instaluj.main([]) == 1
    assert "Nie udało się" in capsys.readouterr().out


def test_inny_system(monkeypatch, capsys):
    monkeypatch.setattr(sys, "platform", "linux")
    assert instaluj.main([]) == 1


def test_wymagane_pliki_istnieja():
    assert PLIK_IKONY.exists()
    assert instaluj.PLIK_STARTOWY == KATALOG_PROJEKTU / "main.py"
    assert instaluj.PLIK_STARTOWY.exists()
