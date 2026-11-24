"""Ekran transakcji: dodawanie, lista, szukanie, edycja i usuwanie."""

from dataclasses import replace

from skarbonka.config import ROZMIAR_STRONY
from skarbonka.models.transakcja import Przelew, Przychod, Transakcja, Wydatek
from skarbonka.services.transakcje import (
    SORTOWANIA,
    posortuj,
    strony,
    suma_przychodow,
    suma_wydatkow,
)
from skarbonka.ui import widoki
from skarbonka.ui.menu import Ekran, OpcjaMenu
from skarbonka.ui.wejscie import (
    potwierdz,
    wczytaj_date,
    wczytaj_date_opcjonalna,
    wczytaj_fraze,
    wczytaj_kwote,
    wczytaj_numer,
    wczytaj_tekst,
    wybierz,
    wybierz_lub_wszystkie,
)
from skarbonka.wyjatki import NieZnalezionoRekordu


class EkranTransakcji(Ekran):
    """Wszystko, co można zrobić z transakcjami."""

    TYTUL = "Transakcje"

    def opcje(self) -> list[OpcjaMenu]:
        return [
            OpcjaMenu("Dodaj wydatek", lambda: self.dodaj(Wydatek)),
            OpcjaMenu("Dodaj przychód", lambda: self.dodaj(Przychod)),
            OpcjaMenu("Przelew między kontami", self.dodaj_przelew),
            OpcjaMenu("Lista transakcji", self.pokaz_liste),
            OpcjaMenu("Szukaj i filtruj", self.szukaj),
            OpcjaMenu("Edytuj transakcję", self.edytuj),
            OpcjaMenu("Usuń transakcję", self.usun),
        ]

    def dodaj(self, rodzaj: type[Transakcja]) -> None:
        """Wczytuje dane i dodaje transakcję podanego rodzaju."""
        konto = wybierz("Konto", self.serwisy.konta.wszystkie())
        kwota = wczytaj_kwote()
        data = wczytaj_date()
        opis = wczytaj_tekst("Opis")
        kategoria = wybierz("Kategoria", self.serwisy.kategorie.pasujace(rodzaj))
        self._zapisz(rodzaj(data, kwota, opis, konto.id, kategoria.id))

    def dodaj_przelew(self) -> None:
        """Wczytuje dane i dodaje przelew między dwoma kontami."""
        konta = self.serwisy.konta.wszystkie()
        if len(konta) < 2:
            widoki.blad("Przelew wymaga co najmniej dwóch kont.")
            return
        zrodlo = wybierz("Z konta", konta)
        cel = wybierz("Na konto", [k for k in konta if k.id != zrodlo.id])
        kwota = wczytaj_kwote()
        data = wczytaj_date()
        opis = f"{zrodlo.nazwa} -> {cel.nazwa}"
        self._zapisz(Przelew(data, kwota, opis, zrodlo.id, konto_docelowe_id=cel.id))

    def pokaz_liste(self) -> None:
        """Wypisuje wszystkie transakcje strona po stronie."""
        self._wypisz(posortuj(self.serwisy.transakcje.wszystkie()))

    def szukaj(self) -> None:
        """Wypisuje transakcje spełniające podane warunki wraz z sumami."""
        od = wczytaj_date_opcjonalna("Od dnia")
        do = wczytaj_date_opcjonalna("Do dnia")
        konto = wybierz_lub_wszystkie("Konto", self.serwisy.konta.wszystkie())
        kategoria = wybierz_lub_wszystkie("Kategoria", self.serwisy.kategorie.wszystkie())
        fraza = wczytaj_fraze("Fragment opisu")
        sposob = wybierz("Kolejność", list(SORTOWANIA), "od najnowszych")
        wybrane = self.serwisy.transakcje.filtruj(
            od,
            do,
            konto_id=konto.id if konto else None,
            kategoria_id=kategoria.id if kategoria else None,
            fraza=fraza,
        )
        self._wypisz(posortuj(wybrane, sposob))
        if wybrane:
            widoki.pokaz_kwoty(
                {"Przychody": suma_przychodow(wybrane), "Wydatki": suma_wydatkow(wybrane)}
            )

    def edytuj(self) -> None:
        """Zmienia wybraną transakcję. Enter zostawia dotychczasową wartość."""
        stara = self._wskaz()
        zmiany = {
            "kwota": wczytaj_kwote(domyslna=stara.kwota),
            "data": wczytaj_date(domyslna=stara.data),
            "opis": wczytaj_tekst("Opis", domyslna=stara.opis),
        }
        pasujace = self.serwisy.kategorie.pasujace(type(stara))
        if pasujace:
            obecna = self.serwisy.kategorie.pobierz(stara.kategoria_id)
            zmiany["kategoria_id"] = wybierz("Kategoria", pasujace, obecna).id
            obecne = self.serwisy.konta.pobierz(stara.konto_id)
            zmiany["konto_id"] = wybierz("Konto", self.serwisy.konta.wszystkie(), obecne).id
        nowa = replace(stara, **zmiany)
        self.serwisy.transakcje.zmien(nowa)
        widoki.sukces(f"Zmieniono: {nowa}")

    def usun(self) -> None:
        """Usuwa wybraną transakcję po potwierdzeniu."""
        transakcja = self._wskaz()
        print(transakcja)
        if potwierdz("Na pewno usunąć?"):
            self.serwisy.transakcje.usun(transakcja)
            widoki.sukces("Usunięto.")

    def _zapisz(self, transakcja: Transakcja) -> None:
        """Dodaje transakcję i potwierdza to na ekranie."""
        self.serwisy.transakcje.dodaj(transakcja)
        widoki.sukces(f"Dodano: {transakcja}")

    def _wskaz(self) -> Transakcja:
        """Pokazuje ostatnie transakcje i zwraca tę o wpisanym numerze."""
        ostatnie = posortuj(self.serwisy.transakcje.wszystkie())[:ROZMIAR_STRONY]
        if not ostatnie:
            raise NieZnalezionoRekordu("Brak transakcji.")
        self._wypisz(ostatnie)
        return self.serwisy.transakcje.pobierz(wczytaj_numer("Numer transakcji"))

    def _wypisz(self, transakcje: list[Transakcja]) -> None:
        """Wypisuje transakcje, pytając o zgodę przed każdą kolejną stroną."""
        if not transakcje:
            print("Brak transakcji.")
            return
        nazwy_kont = self.serwisy.konta.nazwy()
        nazwy_kategorii = self.serwisy.kategorie.nazwy()
        pokazane = 0
        for strona in strony(transakcje, ROZMIAR_STRONY):
            widoki.pokaz_transakcje(strona, nazwy_kont, nazwy_kategorii)
            pokazane += len(strona)
            print(f"Pokazano {pokazane} z {len(transakcje)}")
            if pokazane < len(transakcje) and not potwierdz("Następna strona?"):
                break
