"""Testy przechowywania danych."""

import pytest

from skarbonka.models.kategoria import Kategoria
from skarbonka.storage.repozytoria import Repozytorium
from skarbonka.wyjatki import NieZnalezionoRekordu


@pytest.fixture
def repozytorium() -> Repozytorium[Kategoria]:
    wynik = Repozytorium()
    wynik.dodaj(Kategoria("Jedzenie"))
    wynik.dodaj(Kategoria("Transport"))
    return wynik


def test_dodawanie_nadaje_numery(repozytorium):
    assert [k.id for k in repozytorium.wszystkie()] == [1, 2]
    assert len(repozytorium) == 2


def test_numer_usunietego_nie_wraca(repozytorium):
    repozytorium.usun(2)
    assert repozytorium.dodaj(Kategoria("Zdrowie")).id == 3


def test_zmiana(repozytorium):
    repozytorium.zmien(Kategoria("Auto", id=2))
    assert repozytorium.pobierz(2).nazwa == "Auto"


def test_lista_jest_kopia(repozytorium):
    repozytorium.wszystkie().clear()
    assert len(repozytorium) == 2


@pytest.mark.parametrize("operacja", ["pobierz", "usun"])
def test_brak_rekordu(repozytorium, operacja):
    with pytest.raises(NieZnalezionoRekordu):
        getattr(repozytorium, operacja)(99)


def test_zmiana_nieistniejacego(repozytorium):
    with pytest.raises(NieZnalezionoRekordu):
        repozytorium.zmien(Kategoria("X", id=99))
