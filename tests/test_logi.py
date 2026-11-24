"""Testy zapisywania logów."""

import logging

import pytest

from skarbonka.utils.logi import skonfiguruj_logi


@pytest.fixture(autouse=True)
def sprzatanie():
    """Po teście zamyka pliki otwarte przez logowanie."""
    logger = logging.getLogger("skarbonka")
    yield
    for wyjscie in logger.handlers[:]:
        logger.removeHandler(wyjscie)
        wyjscie.close()
    logger.setLevel(logging.NOTSET)


def test_log_trafia_do_pliku(tmp_path):
    plik = tmp_path / "logi" / "test.log"
    assert skonfiguruj_logi(plik) is True
    logging.getLogger("skarbonka.test").info("zażółć")
    assert "zażółć" in plik.read_text(encoding="utf-8")


def test_szczegolowe_logi(tmp_path):
    plik = tmp_path / "test.log"
    skonfiguruj_logi(plik, szczegolowe=True)
    logging.getLogger("skarbonka.test").debug("drobiazg")
    assert "drobiazg" in plik.read_text(encoding="utf-8")


def test_brak_mozliwosci_zapisu(tmp_path):
    przeszkoda = tmp_path / "plik"
    przeszkoda.write_text("to nie jest katalog", encoding="utf-8")
    assert skonfiguruj_logi(przeszkoda / "test.log") is False
