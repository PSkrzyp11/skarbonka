"""Ekran reguł, które same przypisują kategorie."""

from skarbonka.config import MAKS_DLUGOSC_NAZWY
from skarbonka.ui import widoki
from skarbonka.ui.menu import Ekran, OpcjaMenu
from skarbonka.ui.wejscie import potwierdz, wczytaj_liczbe, wczytaj_tekst, wybierz

MAKS_PRIORYTET = 100


class EkranRegul(Ekran):
    """Zarządzanie regułami."""

    TYTUL = "Reguły kategorii"

    def opcje(self) -> list[OpcjaMenu]:
        return [
            OpcjaMenu("Lista reguł", self.pokaz),
            OpcjaMenu("Dodaj regułę", self.dodaj),
            OpcjaMenu("Usuń regułę", self.usun),
            OpcjaMenu("Zastosuj do transakcji z kategorii „Inne”", self.zastosuj),
        ]

    def pokaz(self) -> None:
        """Wypisuje reguły w kolejności sprawdzania."""
        reguly = self.serwisy.kategoryzator.wszystkie()
        nazwy = self.serwisy.kategorie.nazwy()
        if not reguly:
            print("Brak reguł.")
        for regula in reguly:
            print(f"„{regula.fraza}” -> {nazwy[regula.kategoria_id]} (priorytet {regula.priorytet})")

    def dodaj(self) -> None:
        """Wczytuje dane i dodaje regułę."""
        fraza = wczytaj_tekst("Fragment opisu", MAKS_DLUGOSC_NAZWY)
        kategoria = wybierz("Kategoria", self.serwisy.kategorie.wszystkie())
        priorytet = wczytaj_liczbe("Priorytet", MAKS_PRIORYTET, domyslna=0)
        self.serwisy.kategoryzator.dodaj(fraza, kategoria, priorytet)
        widoki.sukces(f"Dodano regułę „{fraza}” -> {kategoria}.")

    def usun(self) -> None:
        """Usuwa wybraną regułę po potwierdzeniu."""
        regula = wybierz("Reguła do usunięcia", self.serwisy.kategoryzator.wszystkie())
        if potwierdz(f"Na pewno usunąć „{regula}”?"):
            self.serwisy.kategoryzator.usun(regula)
            widoki.sukces("Usunięto.")

    def zastosuj(self) -> None:
        """Uruchamia reguły na zapisanych transakcjach."""
        widoki.sukces(f"Zmienione transakcje: {self.serwisy.kategoryzator.zastosuj()}")
