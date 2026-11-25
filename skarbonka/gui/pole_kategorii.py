"""Wybór kategorii, w którym można od razu dodać nową."""

from typing import TYPE_CHECKING

from skarbonka.gui.formularz import Pole
from skarbonka.gui.zakladka_listy import parser_nazwy
from skarbonka.models.kategoria import Kategoria
from skarbonka.models.transakcja import Transakcja, Wydatek

if TYPE_CHECKING:
    from skarbonka.gui.okno import Okno


def pole_kategorii(okno: "Okno", rodzaj: type[Transakcja], obecna: str = "") -> Pole:
    """Tworzy pole z kategoriami pasującymi do rodzaju transakcji."""
    kategorie = okno.serwisy.kategorie

    def nowa(tekst: str) -> Kategoria:
        nazwa = parser_nazwy(kategorie.sprawdz_nazwe)(tekst)
        return kategorie.dodaj(nazwa, czy_wydatek=issubclass(rodzaj, Wydatek))

    wybor = {k.nazwa: k for k in kategorie.pasujace(rodzaj)}
    return Pole(
        "kategoria", "Kategoria", wartosc=obecna, wybor=wybor, rodzaj="kafelki", nowa=nowa
    )
