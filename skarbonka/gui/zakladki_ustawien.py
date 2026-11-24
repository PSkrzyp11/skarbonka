"""Zakładki ustawień: konta, kategorie, reguły, profile i próg."""

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from tkinter import filedialog
from typing import Any, ClassVar

from skarbonka.config import MAKS_DLUGOSC_NAZWY
from skarbonka.gui import styl
from skarbonka.gui.formularz import Formularz, Pole
from skarbonka.gui.skladniki import Kolumna, Wiersz
from skarbonka.gui.zakladka_listy import ZakladkaListy, parser_nazwy
from skarbonka.models.enums import TypKonta
from skarbonka.models.importy import ProfilCSV
from skarbonka.services.profile import KODOWANIA, MAKS_POMINIETYCH_LINII, SEPARATORY
from skarbonka.utils.formatowanie import formatuj_kwote
from skarbonka.utils.walidacja import parsuj_kwote, parsuj_liczbe, sprawdz_tekst
from skarbonka.wyjatki import BladWalidacji

OPOZNIENIE = 150
MAKS_PRIORYTET = 100
WYDATKI, PRZYCHODY = "wydatki", "przychody"


def _saldo(tekst: str) -> Decimal:
    """Zwraca saldo początkowe, które może być ujemne."""
    return parsuj_kwote(tekst, minimum=None)


class ZakladkaKonta(ZakladkaListy):
    """Konta z saldami."""

    KOLUMNY: ClassVar = [
        Kolumna("Nazwa", 220, rozciagliwa=True),
        Kolumna("Typ", 200),
        Kolumna("Saldo", 150, do_prawej=True),
    ]

    def wiersze(self) -> list[Wiersz]:
        wynik = []
        for konto in self.serwisy.konta.wszystkie():
            saldo = self.serwisy.konta.saldo(konto.id)
            wynik.append(
                Wiersz(
                    konto.id,
                    (konto.nazwa, str(konto.typ), formatuj_kwote(saldo)),
                    (konto.nazwa.casefold(), str(konto.typ), saldo),
                    styl.ZLY if saldo < 0 else None,
                )
            )
        return wynik

    def dodaj(self) -> Formularz:
        def zapisz(dane: dict[str, Any]) -> None:
            self.serwisy.konta.dodaj(dane["nazwa"], dane["typ"], dane["saldo"])

        pola = [
            Pole("nazwa", "Nazwa", parser_nazwy(self.serwisy.konta.sprawdz_nazwe)),
            Pole("typ", "Typ", wybor={str(typ): typ for typ in TypKonta}),
            Pole("saldo", "Saldo początkowe w zł", _saldo, "0"),
        ]
        return Formularz(self.okno, "Nowe konto", pola, zapisz, "Dodaj")

    def usun_rekord(self, numer: int) -> None:
        self.serwisy.konta.usun(self.serwisy.konta.pobierz(numer))


class ZakladkaKategorie(ZakladkaListy):
    """Kategorie wydatków i przychodów."""

    KOLUMNY: ClassVar = [Kolumna("Nazwa", 260, rozciagliwa=True), Kolumna("Rodzaj", 200)]

    def wiersze(self) -> list[Wiersz]:
        return [
            Wiersz(k.id, (k.nazwa, WYDATKI if k.czy_wydatek else PRZYCHODY))
            for k in self.serwisy.kategorie.wszystkie()
        ]

    def dodaj(self) -> Formularz:
        def zapisz(dane: dict[str, Any]) -> None:
            self.serwisy.kategorie.dodaj(dane["nazwa"], dane["czy_wydatek"])

        pola = [
            Pole("nazwa", "Nazwa", parser_nazwy(self.serwisy.kategorie.sprawdz_nazwe)),
            Pole("czy_wydatek", "Rodzaj", wybor={WYDATKI: True, PRZYCHODY: False}),
        ]
        return Formularz(self.okno, "Nowa kategoria", pola, zapisz, "Dodaj")

    def usun_rekord(self, numer: int) -> None:
        self.serwisy.kategorie.usun(self.serwisy.kategorie.pobierz(numer))


class ZakladkaReguly(ZakladkaListy):
    """Reguły, które same przypisują kategorie."""

    KOLUMNY: ClassVar = [
        Kolumna("Opis zawiera", 240, rozciagliwa=True),
        Kolumna("Kategoria", 220),
        Kolumna("Priorytet", 100, do_prawej=True),
    ]

    def wiersze(self) -> list[Wiersz]:
        nazwy = self.serwisy.kategorie.nazwy()
        return [
            Wiersz(
                r.id,
                (r.fraza, nazwy[r.kategoria_id], str(r.priorytet)),
                (r.fraza.casefold(), nazwy[r.kategoria_id], r.priorytet),
            )
            for r in self.serwisy.kategoryzator.wszystkie()
        ]

    def dodaj(self) -> Formularz:
        def zapisz(dane: dict[str, Any]) -> None:
            self.serwisy.kategoryzator.dodaj(dane["fraza"], dane["kategoria"], dane["priorytet"])
            liczba = self.serwisy.kategoryzator.zastosuj()
            self.okno.powiadom(f"Dodano regułę. Zmienione transakcje z kategorii Inne: {liczba}")

        kategorie = {k.nazwa: k for k in self.serwisy.kategorie.wszystkie()}
        pola = [
            Pole(
                "fraza",
                "Fragment opisu",
                lambda tekst: sprawdz_tekst(tekst, "Fragment opisu", MAKS_DLUGOSC_NAZWY),
            ),
            Pole("kategoria", "Kategoria", wybor=kategorie),
            Pole(
                "priorytet", "Priorytet", lambda tekst: parsuj_liczbe(tekst, MAKS_PRIORYTET), "0"
            ),
        ]
        return Formularz(self.okno, "Nowa reguła", pola, zapisz, "Dodaj")

    def usun_rekord(self, numer: int) -> None:
        reguly = {r.id: r for r in self.serwisy.kategoryzator.wszystkie()}
        self.serwisy.kategoryzator.usun(reguly[numer])


class ZakladkaProfile(ZakladkaListy):
    """Układy plików CSV z banków."""

    KOLUMNY: ClassVar = [
        Kolumna("Nazwa", 200, rozciagliwa=True),
        Kolumna("Kolumna daty", 170),
        Kolumna("Kolumna kwoty", 170),
        Kolumna("Kolumna opisu", 170),
    ]

    def wiersze(self) -> list[Wiersz]:
        return [
            Wiersz(numer, (p.nazwa, p.kolumna_data, p.kolumna_kwota, p.kolumna_opis))
            for numer, p in enumerate(self.serwisy.profile.wszystkie())
        ]

    def dodaj(self) -> Formularz | None:
        plik = filedialog.askopenfilename(parent=self.okno, filetypes=[("Plik CSV", "*.csv")])
        if not plik:
            return None

        def dalej(dane: dict[str, Any]) -> None:
            profil = ProfilCSV(dane["nazwa"], dane["separator"], dane["kodowanie"], dane["pomin"])
            kolumny = self.serwisy.profile.kolumny(Path(plik), profil)
            self.okno.after(OPOZNIENIE, lambda: self.wybierz_kolumny(profil, kolumny))

        pola = [
            Pole("nazwa", "Nazwa profilu", parser_nazwy(self.serwisy.profile.sprawdz_nazwe)),
            Pole("separator", "Separator", wybor=SEPARATORY),
            Pole("kodowanie", "Kodowanie", wybor=KODOWANIA),
            Pole(
                "pomin",
                "Ile linii jest przed nagłówkami",
                lambda tekst: parsuj_liczbe(tekst, MAKS_POMINIETYCH_LINII),
                "0",
            ),
        ]
        return Formularz(self.okno, "Nowy profil CSV", pola, dalej, "Dalej")

    def wybierz_kolumny(self, profil: ProfilCSV, kolumny: list[str]) -> Formularz:
        """Pyta o znaczenie kolumn i zapisuje profil."""

        def zapisz(dane: dict[str, Any]) -> None:
            self.serwisy.profile.dodaj(
                replace(
                    profil,
                    kolumna_data=dane["data"],
                    kolumna_kwota=dane["kwota"],
                    kolumna_opis=dane["opis"],
                )
            )
            self.okno.powiadom(f"Dodano profil {profil.nazwa}.")

        wybor = {kolumna: kolumna for kolumna in kolumny}
        pola = [
            Pole("data", "Kolumna z datą", wybor=wybor),
            Pole("kwota", "Kolumna z kwotą", wybor=wybor),
            Pole("opis", "Kolumna z opisem", wybor=wybor),
        ]
        return Formularz(self.okno, f"Kolumny: {profil.nazwa}", pola, zapisz, "Dodaj")

    def usun_rekord(self, numer: int) -> None:
        profil = self.serwisy.profile.wszystkie()[numer]
        if profil not in self.serwisy.profile.wlasne():
            raise BladWalidacji("Wbudowanego profilu nie można usunąć.")
        self.serwisy.profile.usun(profil)
