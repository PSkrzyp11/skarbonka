"""Testy danych demonstracyjnych."""

from datetime import date, timedelta

import pytest

from skarbonka import demo
from skarbonka.models.enums import StanBudzetu
from skarbonka.services.zestaw import dodaj_dane_startowe, utworz_serwisy
from skarbonka.storage.baza import W_PAMIECI, Baza

DZIS = date(2026, 11, 24)


def serwisy_demo(tmp_path, dzis):
    baza = Baza(W_PAMIECI)
    serwisy = utworz_serwisy(baza, tmp_path)
    dodaj_dane_startowe(serwisy)
    demo.wypelnij(baza, serwisy, dzis)
    return baza, serwisy


def test_dane_sa_powtarzalne(tmp_path):
    baza_a, a = serwisy_demo(tmp_path, DZIS)
    baza_b, b = serwisy_demo(tmp_path, DZIS)
    assert a.transakcje.wszystkie() == b.transakcje.wszystkie()
    assert len(a.transakcje.wszystkie()) > 150
    baza_a.zamknij()
    baza_b.zamknij()


def test_demo_pokazuje_wszystkie_funkcje(tmp_path):
    baza, serwisy = serwisy_demo(tmp_path, DZIS)
    stany = {w.kategoria: w.stan for w in serwisy.budzety.wykonanie(DZIS)}
    assert stany["Jedzenie"] is StanBudzetu.PRZEKROCZONY
    assert stany["Transport"] is StanBudzetu.UWAGA
    assert stany["Rozrywka"] is StanBudzetu.W_NORMIE
    assert [(c.nazwa, t) for c, t in serwisy.cykliczne.zalegle(DZIS)] == [
        ("Internet", date(2026, 11, 5))
    ]
    prognoza = serwisy.prognoza.policz(DZIS)
    assert prognoza.pesymistyczna < prognoza.realistyczna < prognoza.optymistyczna
    assert len(serwisy.cele.wszystkie()) == 2
    assert all(t.data <= DZIS for t in serwisy.transakcje.wszystkie())
    baza.zamknij()


@pytest.mark.parametrize("dni", [0, 1, 4, 30, 59, 98, 462])
def test_demo_dziala_w_roznych_dniach(tmp_path, dni):
    dzis = date(2026, 11, 30) + timedelta(days=dni)
    baza, serwisy = serwisy_demo(tmp_path, dzis)
    assert len(serwisy.cykliczne.zalegle(dzis)) == 1
    assert all(t.data <= dzis for t in serwisy.transakcje.wszystkie())
    baza.zamknij()
