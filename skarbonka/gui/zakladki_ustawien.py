"""Zakładki ustawień: konta, kategorie, reguły i profile."""

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from tkinter import filedialog
from typing import Any

from skarbonka.config import MAKS_DLUGOSC_NAZWY
from skarbonka.gui import ikony, styl
from skarbonka.gui.formularz import Formularz, Pole
from skarbonka.gui.lista import Pozycja
from skarbonka.gui.pozycje import kwota_ze_znakiem
from skarbonka.gui.zakladka_listy import ZakladkaListy, parser_nazwy
from skarbonka.models.enums import TypKonta
from skarbonka.models.importy import ProfilCSV
from skarbonka.services.profile import (
    KODOWANIA,
    MAKS_POMINIETYCH_LINII,
    PROFIL_SKARBONKI,
    SEPARATORY,
)
from skarbonka.utils.formatowanie import formatuj_kwote
from skarbonka.utils.walidacja import parsuj_kwote, parsuj_liczbe, sprawdz_tekst
from skarbonka.wyjatki import BladWalidacji

OPOZNIENIE = 30
MAKS_PRIORYTET = 100
WYDATKI, PRZYCHODY = "wydatki", "przychody"
IKONY_KONT = {
    TypKonta.GOTOWKA: ikony.KARTA,
    TypKonta.BIEZACE: ikony.BANK,
    TypKonta.OSZCZEDNOSCI: ikony.ARCHIWUM,
}


def _saldo(tekst: str) -> Decimal:
    """Zwraca saldo początkowe, które może być ujemne."""
    return parsuj_kwote(tekst, minimum=None)


class ZakladkaKonta(ZakladkaListy):
    """Konta z saldami."""

    OPIS = "Gotówka, konta bankowe i oszczędności"

    def pozycje(self) -> list[Pozycja]:
        wynik = []
        for konto in self.serwisy.konta.wszystkie():
            saldo = self.serwisy.konta.saldo(konto.id)
            wynik.append(
                Pozycja(
                    konto.id,
                    IKONY_KONT[konto.typ],
                    konto.nazwa,
                    str(konto.typ),
                    kwota_ze_znakiem(formatuj_kwote(saldo)),
                    kolor=styl.ZLY if saldo < 0 else styl.TEKST,
                )
            )
        return wynik

    def dodaj(self) -> Formularz:
        def zapisz(dane: dict[str, Any]) -> None:
            self.serwisy.konta.dodaj(dane["nazwa"], dane["typ"], dane["saldo"])
            self.okno.powiadom(f"Dodano konto {dane['nazwa']}.")

        pola = [
            Pole("saldo", "Obecne saldo", _saldo, "0", rodzaj="kwota"),
            Pole("nazwa", "Nazwa", parser_nazwy(self.serwisy.konta.sprawdz_nazwe)),
            Pole("typ", "Typ", wybor={str(typ): typ for typ in TypKonta}),
        ]
        return Formularz(self.okno, "Nowe konto", pola, zapisz, "Dodaj konto")

    def usun_rekord(self, numer: int) -> None:
        self.serwisy.konta.usun(self.serwisy.konta.pobierz(numer))


class ZakladkaKategorie(ZakladkaListy):
    """Kategorie wydatków i przychodów."""

    OPIS = "Ikona dobiera się sama na podstawie nazwy"

    def pozycje(self) -> list[Pozycja]:
        return [
            Pozycja(
                k.id,
                ikony.dla_nazwy(k.nazwa),
                k.nazwa,
                WYDATKI if k.czy_wydatek else PRZYCHODY,
                wyrozniona=not k.czy_wydatek,
            )
            for k in self.serwisy.kategorie.wszystkie()
        ]

    def dodaj(self) -> Formularz:
        def zapisz(dane: dict[str, Any]) -> None:
            self.serwisy.kategorie.dodaj(dane["nazwa"], dane["czy_wydatek"])
            self.okno.powiadom(f"Dodano kategorię {dane['nazwa']}.")

        pola = [
            Pole("nazwa", "Nazwa", parser_nazwy(self.serwisy.kategorie.sprawdz_nazwe)),
            Pole("czy_wydatek", "Rodzaj", wybor={WYDATKI: True, PRZYCHODY: False}),
        ]
        return Formularz(self.okno, "Nowa kategoria", pola, zapisz, "Dodaj kategorię")

    def usun_rekord(self, numer: int) -> None:
        self.serwisy.kategorie.usun(self.serwisy.kategorie.pobierz(numer))


class ZakladkaReguly(ZakladkaListy):
    """Reguły, które same przypisują kategorie."""

    OPIS = "Opis z podanym słowem dostaje kategorię automatycznie"
    PUSTO = (ikony.METKA, "Na przykład: biedronka to Jedzenie.")

    def pozycje(self) -> list[Pozycja]:
        nazwy = self.serwisy.kategorie.nazwy()
        return [
            Pozycja(
                r.id,
                ikony.dla_nazwy(nazwy[r.kategoria_id]),
                r.fraza,
                nazwy[r.kategoria_id],
                podpis=f"priorytet {r.priorytet}",
            )
            for r in self.serwisy.kategoryzator.wszystkie()
        ]

    def dodaj(self) -> Formularz:
        def zapisz(dane: dict[str, Any]) -> None:
            self.serwisy.kategoryzator.dodaj(dane["fraza"], dane["kategoria"], dane["priorytet"])
            liczba = self.serwisy.kategoryzator.zastosuj()
            self.okno.powiadom(f"Dodano regułę. Zmienione transakcje: {liczba}")

        kategorie = {k.nazwa: k for k in self.serwisy.kategorie.wszystkie()}
        pola = [
            Pole(
                "fraza",
                "Opis zawiera",
                lambda tekst: sprawdz_tekst(tekst, "Fragment opisu", MAKS_DLUGOSC_NAZWY),
            ),
            Pole("kategoria", "Kategoria", wybor=kategorie, rodzaj="kafelki"),
            Pole(
                "priorytet",
                "Priorytet (wyższy wygrywa)",
                lambda tekst: parsuj_liczbe(tekst, MAKS_PRIORYTET),
                "0",
            ),
        ]
        return Formularz(self.okno, "Nowa reguła", pola, zapisz, "Dodaj regułę")

    def usun_rekord(self, numer: int) -> None:
        reguly = {r.id: r for r in self.serwisy.kategoryzator.wszystkie()}
        self.serwisy.kategoryzator.usun(reguly[numer])


class ZakladkaProfile(ZakladkaListy):
    """Układy plików CSV z banków."""

    OPIS = "Jak czytać wyciąg z Twojego banku"

    def pozycje(self) -> list[Pozycja]:
        return [
            Pozycja(
                numer,
                ikony.BANK if p != PROFIL_SKARBONKI else ikony.KARTA,
                p.nazwa,
                ", ".join(p.wymagane_kolumny),
                podpis="wbudowany" if p == PROFIL_SKARBONKI else "",
            )
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
        return Formularz(self.okno, f"Kolumny: {profil.nazwa}", pola, zapisz, "Dodaj profil")

    def usun_rekord(self, numer: int) -> None:
        profil = self.serwisy.profile.wszystkie()[numer]
        if profil == PROFIL_SKARBONKI:
            raise BladWalidacji("Wbudowanego profilu nie można usunąć.")
        self.serwisy.profile.usun(profil)
