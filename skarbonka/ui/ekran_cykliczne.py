"""Ekran stałych przychodów i opłat."""

from dataclasses import replace
from datetime import date

from skarbonka.config import MAKS_DLUGOSC_NAZWY
from skarbonka.models.cykliczna import KLASY_CYKLICZNE, Cykliczna
from skarbonka.models.enums import Czestotliwosc
from skarbonka.services.cykliczne import NAJSTARSZY_START, do_zaplaty
from skarbonka.ui import widoki
from skarbonka.ui.ekran_osoby import EkranOsob
from skarbonka.ui.menu import Ekran, OpcjaMenu
from skarbonka.ui.wejscie import (
    potwierdz,
    wczytaj_kwote,
    wczytaj_nazwe,
    wczytaj_tekst,
    wczytaj_termin,
    wybierz,
)
from skarbonka.utils.formatowanie import formatuj_date, formatuj_kwote, formatuj_procent

ZAKSIEGUJ, POMIN, POZNIEJ = "zaksięguj", "pomiń ten termin", "zdecyduj później"


class EkranCyklicznych(Ekran):
    """Czynsz, abonamenty, pensja i inne stałe pozycje."""

    TYTUL = "Stałe przychody i opłaty"

    def opcje(self) -> list[OpcjaMenu]:
        return [
            OpcjaMenu("Lista i ile zostaje na czysto", self.pokaz),
            OpcjaMenu("Dodaj", self.dodaj),
            OpcjaMenu("Zaksięguj zaległe", self.zaksieguj),
            OpcjaMenu("Włącz / wyłącz", self.przelacz),
            OpcjaMenu("Usuń", self.usun),
            OpcjaMenu("Edytuj", self.edytuj),
            OpcjaMenu("Płatności w tym miesiącu", self.pokaz_harmonogram),
            OpcjaMenu("Osoby", EkranOsob(self.serwisy).uruchom),
        ]

    def pokaz(self) -> None:
        """Wypisuje stałe pozycje i miesięczny bilans."""
        if not self.serwisy.cykliczne.wszystkie():
            print("Brak stałych pozycji.")
            return
        widoki.pokaz_cykliczne(self.serwisy.cykliczne.grupy())
        bilans = self.serwisy.cykliczne.bilans()
        widoki.pokaz_kwoty(
            {
                "Przychody miesięcznie": bilans.przychody,
                "Opłaty miesięcznie": bilans.wydatki,
                "Zostaje na czysto": bilans.na_czysto,
                "Na czysto dziennie": bilans.dziennie,
            }
        )
        if bilans.procent is not None:
            print(f"To {formatuj_procent(bilans.procent)} stałych przychodów.")

    def pokaz_harmonogram(self) -> None:
        """Wypisuje terminy z bieżącego miesiąca i starsze zaległości."""
        platnosci = self.serwisy.cykliczne.harmonogram()
        if not platnosci:
            print("Brak płatności w tym miesiącu.")
            return
        widoki.pokaz_harmonogram(platnosci, self.serwisy.cykliczne.opis)
        print(f"Zostało do zapłaty: {formatuj_kwote(do_zaplaty(platnosci))}")

    def edytuj(self) -> None:
        """Zmienia wybraną pozycję. Enter zostawia dotychczasową wartość."""
        stara = self._wybierz_stala("Pozycja")
        nowa = replace(
            stara,
            nazwa=wczytaj_tekst("Nazwa", MAKS_DLUGOSC_NAZWY, stara.nazwa),
            kwota=wczytaj_kwote(domyslna=stara.kwota),
        )
        czestotliwosc = wybierz("Częstotliwość", list(Czestotliwosc), stara.czestotliwosc)
        najstarszy = date.today() - NAJSTARSZY_START
        termin = wczytaj_termin("Następny termin", najstarszy, stara.nastepny)
        nowa = nowa.przeplanuj(termin, czestotliwosc)
        nowa.osoba_id = self._wybierz_osobe(stara.osoba_id)
        self.serwisy.cykliczne.zmien(nowa)
        widoki.sukces(f"Zmieniono: {nowa}")

    def dodaj(self) -> None:
        """Wczytuje dane i dodaje transakcję cykliczną."""
        osoba_id = self._wybierz_osobe()
        nazwa = wczytaj_nazwe(
            "Nazwa", lambda tekst: self.serwisy.cykliczne.sprawdz_nazwe(tekst, osoba_id)
        )
        rodzaj = wybierz("Rodzaj", list(KLASY_CYKLICZNE))
        kwota = wczytaj_kwote()
        konto = wybierz("Konto", self.serwisy.konta.wszystkie())
        pasujace = self.serwisy.kategorie.pasujace(KLASY_CYKLICZNE[rodzaj])
        kategoria = wybierz("Kategoria", pasujace)
        czestotliwosc = wybierz("Częstotliwość", list(Czestotliwosc))
        start = wczytaj_termin("Pierwszy termin", date.today() - NAJSTARSZY_START)
        self.serwisy.cykliczne.dodaj(
            Cykliczna(
                nazwa,
                rodzaj,
                kwota,
                konto.id,
                kategoria.id,
                start,
                czestotliwosc,
                osoba_id=osoba_id,
            )
        )
        widoki.sukces(f"Dodano: {nazwa}")

    def _wybierz_osobe(self, domyslna: int | None = None) -> int | None:
        """Pyta o osobę, jeśli jakieś są. Zwraca jej numer albo None dla wspólnych."""
        wybor = self.serwisy.osoby.wybor()
        nazwy = {numer: nazwa for nazwa, numer in wybor.items()}
        if len(wybor) == 1:
            return None
        return wybor[wybierz("Osoba", list(wybor), nazwy[domyslna])]

    def _wybierz_stala(self, komunikat: str) -> Cykliczna:
        """Pyta o jedną ze stałych pozycji."""
        stale = {self.serwisy.cykliczne.opis(c): c for c in self.serwisy.cykliczne.wszystkie()}
        return stale[wybierz(komunikat, list(stale))]

    def zaksieguj(self) -> None:
        """Pyta o każdy zaległy termin."""
        zalegle = self.serwisy.cykliczne.zalegle()
        if not zalegle:
            print("Nie ma zaległych transakcji.")
        odlozone: set[int] = set()
        for cykliczna, termin in zalegle:
            if cykliczna.id in odlozone:
                continue
            nazwa = self.serwisy.cykliczne.opis(cykliczna)
            opis = f"{formatuj_date(termin)} {nazwa} {formatuj_kwote(cykliczna.wplyw)}"
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
        wybrana = self._wybierz_stala("Pozycja")
        zmieniona = self.serwisy.cykliczne.przelacz(wybrana)
        widoki.sukces(f"{zmieniona}: {'włączona' if zmieniona.aktywna else 'wyłączona'}")

    def usun(self) -> None:
        """Usuwa wybraną pozycję po potwierdzeniu."""
        wybrana = self._wybierz_stala("Pozycja do usunięcia")
        if potwierdz(f"Na pewno usunąć „{wybrana}”?"):
            self.serwisy.cykliczne.usun(wybrana)
            widoki.sukces("Usunięto.")
