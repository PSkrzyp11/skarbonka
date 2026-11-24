"""Zakładka transakcji cyklicznych."""

from datetime import date
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from skarbonka.gui import ikony, styl
from skarbonka.gui.formularz import Formularz, Pole
from skarbonka.gui.lista import Pozycja
from skarbonka.gui.pozycje import kwota_ze_znakiem
from skarbonka.gui.skladniki import Karta, etykieta, kafelek_ikony, przycisk, ramka, wyczysc
from skarbonka.gui.zakladka_listy import ZakladkaListy, parser_nazwy
from skarbonka.models.cykliczna import KLASY_CYKLICZNE, Cykliczna
from skarbonka.models.enums import Czestotliwosc
from skarbonka.services.cykliczne import NAJSTARSZY_START
from skarbonka.utils.formatowanie import formatuj_date, formatuj_kwote
from skarbonka.utils.walidacja import parsuj_date, parsuj_kwote
from skarbonka.wyjatki import BladWalidacji

if TYPE_CHECKING:
    from skarbonka.gui.okno import Okno

ILE_ZALEGLYCH = 3


class ZakladkaCykliczne(ZakladkaListy):
    """Stałe przychody i wydatki."""

    OPIS = "Pensja, czynsz i abonamenty, które się powtarzają"
    PUSTO = (ikony.POWTARZANIE, "Dodaj czynsz, pensję albo abonament.")

    def __init__(self, rodzic: Any, okno: "Okno") -> None:
        super().__init__(rodzic, okno)
        self.serwis = okno.serwisy.cykliczne
        self._zalegle = Karta(self, "Czeka na zaksięgowanie")
        self._lista_zaleglych = ramka(self._zalegle)
        self._lista_zaleglych.pack(fill="x", padx=20, pady=(0, 16))

    def dodaj_akcje(self, rzad: ctk.CTkFrame) -> None:
        przycisk(rzad, "Włącz lub wyłącz", self.przelacz, "glowny", 130, 34).pack(side="right")

    def pozycje(self) -> list[Pozycja]:
        return [
            Pozycja(
                c.id,
                ikony.dla_nazwy(c.nazwa, ikony.POWTARZANIE),
                c.nazwa,
                f"{c.czestotliwosc}  ·  od {formatuj_date(c.start)}"
                + ("" if c.aktywna else "  ·  wyłączona"),
                kwota_ze_znakiem(formatuj_kwote(c.wplyw)),
                f"ostatnio {formatuj_date(c.ostatnia)}" if c.ostatnia else "jeszcze nie księgowana",
                styl.DOBRY if c.wplyw > 0 else styl.TEKST,
                wyrozniona=c.wplyw > 0,
            )
            for c in self.serwisy.cykliczne.wszystkie()
        ]

    def odswiez(self) -> None:
        super().odswiez()
        wyczysc(self._lista_zaleglych)
        zalegle = self.serwis.zalegle()
        if not zalegle:
            self._zalegle.pack_forget()
            return
        self._zalegle.pack(side="bottom", fill="x", pady=(16, 0))
        for cykliczna, termin in zalegle[:ILE_ZALEGLYCH]:
            self._dodaj_zalegla(cykliczna, termin)
        reszta = len(zalegle) - ILE_ZALEGLYCH
        if reszta > 0:
            etykieta(
                self._lista_zaleglych, f"Kolejne terminy: {reszta}", kolor=styl.TEKST_DRUGI
            ).pack(anchor="w", pady=(6, 0))

    def _dodaj_zalegla(self, cykliczna: Cykliczna, termin: date) -> None:
        """Dodaje wiersz z zaległym terminem."""
        rzad = ramka(self._lista_zaleglych)
        rzad.pack(fill="x", pady=4)
        kafelek_ikony(rzad, ikony.ZEGAR, styl.UWAGA_TLO, styl.UWAGA, bok=38).pack(side="left")
        napisy = ramka(rzad)
        napisy.pack(side="left", padx=14)
        etykieta(napisy, cykliczna.nazwa, 14, "mocny").pack(anchor="w")
        etykieta(napisy, formatuj_date(termin), 12, kolor=styl.TEKST_DRUGI).pack(anchor="w")
        przycisk(
            rzad, "Zaksięguj", lambda: self.zaksieguj(cykliczna, termin), "glowny", 100, 34
        ).pack(side="right")
        przycisk(rzad, "Pomiń", lambda: self.pomin(cykliczna, termin), "cichy", 70, 34).pack(
            side="right", padx=8
        )
        etykieta(rzad, kwota_ze_znakiem(formatuj_kwote(cykliczna.wplyw)), 16, "liczby").pack(
            side="right", padx=16
        )

    def zaksieguj(self, cykliczna: Cykliczna, termin: date) -> None:
        """Księguje najstarszy termin."""
        self.serwis.zaksieguj(cykliczna, termin)
        self.okno.powiadom(f"Zaksięgowano: {cykliczna}")
        self.okno.odswiez()

    def pomin(self, cykliczna: Cykliczna, termin: date) -> None:
        """Pomija termin."""
        self.serwis.pomin(cykliczna, termin)
        self.okno.powiadom(f"Pominięto termin: {cykliczna}")
        self.okno.odswiez()

    def dodaj(self) -> Formularz:
        serwisy = self.serwisy
        najstarszy = date.today() - NAJSTARSZY_START

        def zapisz(dane: dict[str, Any]) -> None:
            klasa, kategoria = KLASY_CYKLICZNE[dane["rodzaj"]], dane["kategoria"]
            if kategoria not in serwisy.kategorie.pasujace(klasa):
                raise BladWalidacji(f"Kategoria {kategoria} nie pasuje do rodzaju {klasa.RODZAJ}.")
            self.serwis.dodaj(
                Cykliczna(
                    dane["nazwa"],
                    dane["rodzaj"],
                    dane["kwota"],
                    dane["konto"].id,
                    kategoria.id,
                    dane["start"],
                    dane["czestotliwosc"],
                )
            )
            self.okno.powiadom(f"Dodano: {dane['nazwa']}")

        pola = [
            Pole("kwota", "Kwota", parsuj_kwote, rodzaj="kwota"),
            Pole("nazwa", "Nazwa", parser_nazwy(self.serwis.sprawdz_nazwe)),
            Pole("rodzaj", "Rodzaj", wybor={rodzaj: rodzaj for rodzaj in KLASY_CYKLICZNE}),
            Pole(
                "czestotliwosc",
                "Powtarzanie",
                wartosc=str(Czestotliwosc.MIESIAC),
                wybor={str(c): c for c in Czestotliwosc},
            ),
            Pole(
                "start",
                "Pierwszy termin",
                lambda tekst: parsuj_date(tekst, najwczesniej=najstarszy),
                formatuj_date(date.today()),
                rodzaj="data",
            ),
            Pole("konto", "Konto", wybor={k.nazwa: k for k in serwisy.konta.wszystkie()}),
            Pole(
                "kategoria",
                "Kategoria",
                wybor={k.nazwa: k for k in serwisy.kategorie.wszystkie()},
                rodzaj="kafelki",
            ),
        ]
        return Formularz(self.okno, "Nowa płatność", pola, zapisz, "Dodaj")

    def przelacz(self) -> None:
        """Włącza albo wyłącza zaznaczoną pozycję."""
        zmieniona = self.serwis.przelacz(self._wybrana())
        self.okno.powiadom(f"{zmieniona}: {'włączona' if zmieniona.aktywna else 'wyłączona'}")
        self.okno.odswiez()

    def usun_rekord(self, numer: int) -> None:
        self.serwis.usun(self._wybrana())

    def _wybrana(self) -> Cykliczna:
        """Zwraca zaznaczoną pozycję."""
        numer = self.wybrany_numer()
        return next(c for c in self.serwis.wszystkie() if c.id == numer)
