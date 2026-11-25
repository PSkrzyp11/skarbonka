"""Ekran osób, które mają własne stałe przychody i opłaty."""

from skarbonka.ui import widoki
from skarbonka.ui.menu import Ekran, OpcjaMenu
from skarbonka.ui.wejscie import potwierdz, wczytaj_nazwe, wybierz


class EkranOsob(Ekran):
    """Domownicy i to, ile zostaje każdemu na czysto."""

    TYTUL = "Osoby"

    def opcje(self) -> list[OpcjaMenu]:
        return [
            OpcjaMenu("Ile zostaje każdej osobie", self.pokaz),
            OpcjaMenu("Dodaj osobę", self.dodaj),
            OpcjaMenu("Zmień nazwę", self.zmien),
            OpcjaMenu("Usuń osobę", self.usun),
        ]

    def pokaz(self) -> None:
        """Wypisuje bilans każdej osoby."""
        if not self.serwisy.osoby.wszystkie():
            print("Brak osób.")
            return
        widoki.pokaz_osoby(self.serwisy.cykliczne.grupy(), self.serwisy.cykliczne.bilans())

    def dodaj(self) -> None:
        """Dodaje osobę."""
        osoba = self.serwisy.osoby.dodaj(wczytaj_nazwe("Imię", self.serwisy.osoby.sprawdz_nazwe))
        widoki.sukces(f"Dodano: {osoba}")

    def zmien(self) -> None:
        """Zmienia nazwę wybranej osoby."""
        osoby = self.serwisy.osoby
        osoba = wybierz("Osoba", osoby.wszystkie())
        nazwa = wczytaj_nazwe("Nowe imię", lambda tekst: osoby.sprawdz_nazwe(tekst, osoba.id))
        osoby.zmien(osoba, nazwa)
        widoki.sukces(f"Zmieniono: {nazwa}")

    def usun(self) -> None:
        """Usuwa osobę i jej stałe pozycje po potwierdzeniu."""
        osoba = wybierz("Osoba do usunięcia", self.serwisy.osoby.wszystkie())
        if potwierdz(f"Usunąć osobę „{osoba}” i jej stałe pozycje?"):
            self.serwisy.osoby.usun(osoba)
            widoki.sukces("Usunięto.")
