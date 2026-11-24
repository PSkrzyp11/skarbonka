"""Zakładka transakcji cyklicznych."""

from datetime import date
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from skarbonka.gui import styl
from skarbonka.gui.formularz import Formularz, Pole
from skarbonka.gui.skladniki import Karta, Kolumna, Tabela, Wiersz, etykieta, przycisk, wyczysc
from skarbonka.gui.zakladka_listy import parser_nazwy
from skarbonka.models.cykliczna import KLASY_CYKLICZNE, Cykliczna
from skarbonka.models.enums import Czestotliwosc
from skarbonka.services.cykliczne import NAJSTARSZY_START
from skarbonka.utils.formatowanie import formatuj_date, formatuj_kwote
from skarbonka.utils.walidacja import parsuj_date, parsuj_kwote
from skarbonka.wyjatki import BladWalidacji, NieZnalezionoRekordu

if TYPE_CHECKING:
    from skarbonka.gui.okno import Okno

KOLUMNY = [
    Kolumna("Nazwa", 200, rozciagliwa=True),
    Kolumna("Powtarzanie", 120),
    Kolumna("Od", 100),
    Kolumna("Ostatnio", 100),
    Kolumna("Aktywna", 80),
    Kolumna("Kwota", 130, do_prawej=True),
]
ILE_ZALEGLYCH = 4


class ZakladkaCykliczne(ctk.CTkFrame):
    """Stałe przychody i wydatki."""

    def __init__(self, rodzic: Any, okno: "Okno") -> None:
        super().__init__(rodzic)
        self.okno = okno
        self.serwis = okno.serwisy.cykliczne
        gora = ctk.CTkFrame(self, fg_color=styl.PRZEZROCZYSTY)
        gora.pack(fill="x", pady=(6, 10))
        przycisk(gora, "Dodaj", self.dodaj, glowny=True).pack(side="right")
        przycisk(gora, "Usuń", self.usun).pack(side="right", padx=8)
        przycisk(gora, "Włącz / wyłącz", self.przelacz).pack(side="right")
        self._zalegle = Karta(self, "Zaległe")
        self._zalegle.pack(side="bottom", fill="x", pady=(10, 0))
        self._lista_zaleglych = ctk.CTkFrame(self._zalegle, fg_color=styl.PRZEZROCZYSTY)
        self._lista_zaleglych.pack(fill="x", padx=16, pady=(0, 12))
        karta = Karta(self)
        karta.pack(fill="both", expand=True)
        self.tabela = Tabela(karta, KOLUMNY, wysokosc=5)
        self.tabela.pack(fill="both", expand=True, padx=10, pady=10)

    def odswiez(self) -> None:
        """Wypisuje wzory i zaległe terminy."""
        self.tabela.wypelnij(
            [
                Wiersz(
                    c.id,
                    (
                        c.nazwa,
                        str(c.czestotliwosc),
                        formatuj_date(c.start),
                        formatuj_date(c.ostatnia) if c.ostatnia else "-",
                        "tak" if c.aktywna else "nie",
                        formatuj_kwote(c.wplyw),
                    ),
                    (
                        c.nazwa.casefold(),
                        str(c.czestotliwosc),
                        c.start,
                        c.ostatnia or date.min,
                        c.aktywna,
                        c.wplyw,
                    ),
                )
                for c in self.serwis.wszystkie()
            ]
        )
        self._pokaz_zalegle()

    def _pokaz_zalegle(self) -> None:
        """Wypisuje najstarsze zaległe terminy z przyciskami."""
        wyczysc(self._lista_zaleglych)
        zalegle = self.serwis.zalegle()
        if not zalegle:
            etykieta(self._lista_zaleglych, "Nic nie czeka.", kolor=styl.TEKST_DRUGI).pack(
                anchor="w"
            )
        for cykliczna, termin in zalegle[:ILE_ZALEGLYCH]:
            rzad = ctk.CTkFrame(self._lista_zaleglych, fg_color=styl.PRZEZROCZYSTY)
            rzad.pack(fill="x", pady=2)
            opis = f"{formatuj_date(termin)}   {cykliczna}   {formatuj_kwote(cykliczna.wplyw)}"
            etykieta(rzad, opis).pack(side="left")
            przycisk(
                rzad, "Zaksięguj", lambda c=cykliczna, t=termin: self.zaksieguj(c, t), glowny=True
            ).pack(side="right")
            przycisk(rzad, "Pomiń", lambda c=cykliczna, t=termin: self.pomin(c, t)).pack(
                side="right", padx=8
            )
        reszta = len(zalegle) - ILE_ZALEGLYCH
        if reszta > 0:
            etykieta(
                self._lista_zaleglych, f"Kolejne terminy: {reszta}", kolor=styl.TEKST_DRUGI
            ).pack(anchor="w")

    def zaksieguj(self, cykliczna: Cykliczna, termin: date) -> None:
        """Księguje najstarszy termin."""
        self.serwis.zaksieguj(cykliczna, termin)
        self.okno.powiadom(f"Zaksięgowano: {cykliczna}")
        self.odswiez()

    def pomin(self, cykliczna: Cykliczna, termin: date) -> None:
        """Pomija termin."""
        self.serwis.pomin(cykliczna, termin)
        self.okno.powiadom(f"Pominięto termin: {cykliczna}")
        self.odswiez()

    def dodaj(self) -> Formularz:
        """Otwiera formularz nowej transakcji cyklicznej."""
        serwisy = self.okno.serwisy
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
            Pole("nazwa", "Nazwa", parser_nazwy(self.serwis.sprawdz_nazwe)),
            Pole("rodzaj", "Rodzaj", wybor={rodzaj: rodzaj for rodzaj in KLASY_CYKLICZNE}),
            Pole("kwota", "Kwota w zł", parsuj_kwote),
            Pole("konto", "Konto", wybor={k.nazwa: k for k in serwisy.konta.wszystkie()}),
            Pole(
                "kategoria", "Kategoria", wybor={k.nazwa: k for k in serwisy.kategorie.wszystkie()}
            ),
            Pole(
                "czestotliwosc",
                "Częstotliwość",
                wartosc=str(Czestotliwosc.MIESIAC),
                wybor={str(c): c for c in Czestotliwosc},
            ),
            Pole(
                "start",
                "Pierwszy termin",
                lambda tekst: parsuj_date(tekst, najwczesniej=najstarszy),
                formatuj_date(date.today()),
            ),
        ]
        return Formularz(self.okno, "Nowa transakcja cykliczna", pola, zapisz, "Dodaj")

    def przelacz(self) -> None:
        """Włącza albo wyłącza zaznaczoną pozycję."""
        self.serwis.przelacz(self._zaznaczona())
        self.odswiez()

    def usun(self) -> None:
        """Usuwa zaznaczoną pozycję po potwierdzeniu."""
        wybrana = self._zaznaczona()
        if self.okno.zapytaj(f"Usunąć „{wybrana}”? Zaksięgowane transakcje zostaną."):
            self.serwis.usun(wybrana)
            self.odswiez()

    def _zaznaczona(self) -> Cykliczna:
        """Zwraca zaznaczoną pozycję."""
        numer = self.tabela.zaznaczony()
        for cykliczna in self.serwis.wszystkie():
            if cykliczna.id == numer:
                return cykliczna
        raise NieZnalezionoRekordu("Najpierw zaznacz pozycję na liście.")
