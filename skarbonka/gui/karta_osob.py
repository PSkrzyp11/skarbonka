"""Karta z osobami: ile zostaje każdej i wybór osoby do pokazania."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from skarbonka.gui import ikony, styl
from skarbonka.gui.formularz import Formularz, Pole
from skarbonka.gui.lista import Lista, Pozycja
from skarbonka.gui.pozycje import kwota_ze_znakiem
from skarbonka.gui.skladniki import Karta, przycisk_ikony, ramka
from skarbonka.gui.zakladka_listy import parser_nazwy
from skarbonka.models.cykliczna import Cykliczna
from skarbonka.models.osoba import Osoba
from skarbonka.services.cykliczne import BilansStalych
from skarbonka.services.osoby import WSZYSCY
from skarbonka.utils.formatowanie import formatuj_kwote

if TYPE_CHECKING:
    from skarbonka.gui.okno import Okno

NUMER_WSZYSTKICH = 0
NUMER_WSPOLNYCH = -1
NAJWIECEJ_WIERSZY = 4
WYSOKOSC_TYTULU = 30


class KartaOsob(Karta):
    """Lista osób. Kliknięcie osoby pokazuje tylko jej pozycje."""

    def __init__(self, rodzic: Any, okno: "Okno", po_wyborze: Callable[[], Any]) -> None:
        super().__init__(rodzic, "Osoby")
        self.okno = okno
        self.serwis = okno.serwisy.osoby
        self.wybrana = NUMER_WSZYSTKICH
        self._po_wyborze = po_wyborze
        self.gora.configure(height=WYSOKOSC_TYTULU)
        self.gora.pack_propagate(False)
        self._akcje = ramka(self.gora)
        przycisk_ikony(self._akcje, ikony.KOSZ, self.usun, bok=30).pack(side="right")
        przycisk_ikony(self._akcje, ikony.OLOWEK, self.edytuj, bok=30).pack(side="right")
        self.lista = Lista(self, self._wybrano)
        self.lista.pack(fill="x", padx=8, pady=(0, 10))

    def odswiez(self) -> None:
        """Wczytuje osoby i ich bilanse."""
        stale = self.okno.serwisy.cykliczne
        pozycje = [self._pozycja(NUMER_WSZYSTKICH, ikony.LUDZIE, WSZYSCY, stale.bilans())]
        for grupa in stale.grupy():
            if grupa.osoba_id is None:
                pozycje.append(
                    self._pozycja(NUMER_WSPOLNYCH, ikony.DOM, grupa.nazwa, grupa.bilans)
                )
            else:
                pozycje.append(
                    self._pozycja(grupa.osoba_id, ikony.OSOBA, grupa.nazwa, grupa.bilans)
                )
        if self.wybrana not in {p.id for p in pozycje}:
            self.wybrana = NUMER_WSZYSTKICH
        self.lista.ustaw_wysokosc(min(len(pozycje), NAJWIECEJ_WIERSZY))
        self.lista.wypelnij(pozycje)
        self.lista.zaznacz(self.wybrana)
        if self.wybrana > 0:
            self._akcje.pack(side="right")
        else:
            self._akcje.pack_forget()

    @staticmethod
    def _pozycja(numer: int, ikona: str, nazwa: str, bilans: BilansStalych) -> Pozycja:
        """Zamienia bilans na wiersz listy."""
        return Pozycja(
            numer,
            ikona,
            nazwa,
            f"opłaty {formatuj_kwote(bilans.wydatki)}",
            kwota_ze_znakiem(formatuj_kwote(bilans.na_czysto)),
            f"z {formatuj_kwote(bilans.przychody)}" if bilans.przychody else "",
            styl.ZLY if bilans.na_czysto < 0 else styl.TEKST,
        )

    def pasuje(self, stala: Cykliczna) -> bool:
        """Sprawdza, czy pozycja należy do wybranej osoby."""
        return self.wybrana == NUMER_WSZYSTKICH or stala.osoba_id == self.osoba_id()

    def osoba_id(self) -> int | None:
        """Zwraca numer wybranej osoby albo None."""
        return self.wybrana if self.wybrana > 0 else None

    def nazwa_wybranej(self) -> str:
        """Zwraca nazwę wybranego wiersza."""
        return self.lista.pozycja(self.wybrana).tytul

    def _wybrano(self) -> None:
        numer = self.lista.zaznaczony() or NUMER_WSZYSTKICH
        if numer != self.wybrana:
            self.wybrana = numer
            self._po_wyborze()

    def _osoba(self) -> Osoba:
        return self.serwis.pobierz(self.wybrana)

    def dodaj(self) -> Formularz:
        """Otwiera panel nowej osoby."""

        def zapisz(dane: dict[str, Any]) -> None:
            self.wybrana = self.serwis.dodaj(dane["nazwa"]).id
            self.okno.powiadom(f"Dodano: {dane['nazwa']}. Wpisz przychody i opłaty tej osoby.")

        pola = [Pole("nazwa", "Imię", parser_nazwy(self.serwis.sprawdz_nazwe))]
        return Formularz(self.okno, "Nowa osoba", pola, zapisz, "Dodaj osobę")

    def edytuj(self) -> Formularz:
        """Otwiera panel zmiany nazwy wybranej osoby."""
        osoba = self._osoba()

        def zapisz(dane: dict[str, Any]) -> None:
            self.serwis.zmien(osoba, dane["nazwa"])
            self.okno.powiadom("Zapisano zmiany.")

        parser = parser_nazwy(lambda nazwa: self.serwis.sprawdz_nazwe(nazwa, osoba.id))
        pola = [Pole("nazwa", "Imię", parser, osoba.nazwa)]
        return Formularz(self.okno, "Zmiana imienia", pola, zapisz)

    def usun(self) -> None:
        """Usuwa wybraną osobę i jej stałe pozycje po potwierdzeniu."""
        osoba = self._osoba()
        pytanie = f"Usunąć osobę „{osoba}” i jej stałe pozycje? Transakcje zostaną."
        if self.okno.zapytaj(pytanie, "Usuń", grozne=True):
            self.serwis.usun(osoba)
            self.okno.powiadom("Usunięto.")
            self.okno.odswiez()
