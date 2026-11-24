"""Ekran transakcji cyklicznych."""

from datetime import date

from skarbonka.models.cykliczna import KLASY_CYKLICZNE, Cykliczna
from skarbonka.models.enums import Czestotliwosc
from skarbonka.services.cykliczne import NAJSTARSZY_START
from skarbonka.ui import widoki
from skarbonka.ui.menu import Ekran, OpcjaMenu
from skarbonka.ui.wejscie import (
    potwierdz,
    wczytaj_kwote,
    wczytaj_nazwe,
    wczytaj_termin,
    wybierz,
)
from skarbonka.utils.formatowanie import formatuj_date, formatuj_kwote

ZAKSIEGUJ, POMIN, POZNIEJ = "zaksięguj", "pomiń ten termin", "zdecyduj później"


class EkranCyklicznych(Ekran):
    """Czynsz, abonamenty, pensja i inne stałe pozycje."""

    TYTUL = "Transakcje cykliczne"

    def opcje(self) -> list[OpcjaMenu]:
        return [
            OpcjaMenu("Lista", self.pokaz),
            OpcjaMenu("Dodaj", self.dodaj),
            OpcjaMenu("Zaksięguj zaległe", self.zaksieguj),
            OpcjaMenu("Włącz / wyłącz", self.przelacz),
            OpcjaMenu("Usuń", self.usun),
        ]

    def pokaz(self) -> None:
        """Wypisuje wszystkie transakcje cykliczne."""
        cykliczne = self.serwisy.cykliczne.wszystkie()
        if not cykliczne:
            print("Brak transakcji cyklicznych.")
            return
        widoki.pokaz_cykliczne(cykliczne)

    def dodaj(self) -> None:
        """Wczytuje dane i dodaje transakcję cykliczną."""
        nazwa = wczytaj_nazwe("Nazwa", self.serwisy.cykliczne.sprawdz_nazwe)
        rodzaj = wybierz("Rodzaj", list(KLASY_CYKLICZNE))
        kwota = wczytaj_kwote()
        konto = wybierz("Konto", self.serwisy.konta.wszystkie())
        pasujace = self.serwisy.kategorie.pasujace(KLASY_CYKLICZNE[rodzaj])
        kategoria = wybierz("Kategoria", pasujace)
        czestotliwosc = wybierz("Częstotliwość", list(Czestotliwosc))
        start = wczytaj_termin("Pierwszy termin", date.today() - NAJSTARSZY_START)
        self.serwisy.cykliczne.dodaj(
            Cykliczna(nazwa, rodzaj, kwota, konto.id, kategoria.id, start, czestotliwosc)
        )
        widoki.sukces(f"Dodano: {nazwa}")

    def zaksieguj(self) -> None:
        """Pyta o każdy zaległy termin."""
        zalegle = self.serwisy.cykliczne.zalegle()
        if not zalegle:
            print("Nie ma zaległych transakcji.")
        odlozone: set[int] = set()
        for cykliczna, termin in zalegle:
            if cykliczna.id in odlozone:
                continue
            opis = f"{formatuj_date(termin)} {cykliczna} {formatuj_kwote(cykliczna.wplyw)}"
            decyzja = wybierz(opis, [ZAKSIEGUJ, POMIN, POZNIEJ], ZAKSIEGUJ)
            if decyzja == ZAKSIEGUJ:
                transakcja = self.serwisy.cykliczne.zaksieguj(cykliczna, termin)
                widoki.sukces(f"Dodano: {transakcja}")
            elif decyzja == POMIN:
                self.serwisy.cykliczne.pomin(cykliczna, termin)
            else:
                odlozone.add(cykliczna.id)

    def przelacz(self) -> None:
        """Włącza albo wyłącza wybraną pozycję."""
        wybrana = wybierz("Pozycja", self.serwisy.cykliczne.wszystkie())
        zmieniona = self.serwisy.cykliczne.przelacz(wybrana)
        widoki.sukces(f"{zmieniona}: {'włączona' if zmieniona.aktywna else 'wyłączona'}")

    def usun(self) -> None:
        """Usuwa wybraną pozycję po potwierdzeniu."""
        wybrana = wybierz("Pozycja do usunięcia", self.serwisy.cykliczne.wszystkie())
        if potwierdz(f"Na pewno usunąć „{wybrana}”?"):
            self.serwisy.cykliczne.usun(wybrana)
            widoki.sukces("Usunięto.")
