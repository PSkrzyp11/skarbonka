"""Lista transakcji z filtrami."""

from typing import Any

import customtkinter as ctk

from skarbonka.gui import formularze_transakcji as formularze
from skarbonka.gui import styl
from skarbonka.gui.skladniki import Karta, Tabela, etykieta, przycisk
from skarbonka.gui.widok import Widok
from skarbonka.gui.wiersze import KOLUMNY_TRANSAKCJI, wiersze_transakcji
from skarbonka.models.transakcja import Przychod, Transakcja, Wydatek
from skarbonka.services.transakcje import posortuj, suma_przychodow, suma_wydatkow
from skarbonka.utils.formatowanie import formatuj_kwote
from skarbonka.utils.walidacja import parsuj_date
from skarbonka.wyjatki import NieZnalezionoRekordu

WSZYSTKIE = "wszystkie"


class WidokTransakcje(Widok):
    """Przeglądanie, filtrowanie, dodawanie, edycja i usuwanie."""

    TYTUL = "Transakcje"

    def buduj(self) -> None:
        przyciski = (
            ("+ Wydatek", lambda: formularze.nowa_transakcja(self.okno, Wydatek), True),
            ("+ Przychód", lambda: formularze.nowa_transakcja(self.okno, Przychod), False),
            ("+ Przelew", lambda: formularze.nowy_przelew(self.okno), False),
            ("+ Waluta", lambda: formularze.wydatek_w_walucie(self.okno), False),
        )
        for tekst, akcja, glowny in przyciski:
            przycisk(self.pasek, tekst, akcja, glowny).pack(side="left", padx=(8, 0))
        self._buduj_filtry()

        dol = ctk.CTkFrame(self.tresc, fg_color=styl.PRZEZROCZYSTY)
        dol.pack(side="bottom", fill="x", pady=(12, 0))
        self.podsumowanie = etykieta(dol, "", kolor=styl.TEKST_DRUGI)
        self.podsumowanie.pack(side="left")
        przycisk(dol, "Usuń", self.usun).pack(side="right")
        przycisk(dol, "Edytuj", self.edytuj).pack(side="right", padx=8)

        karta = Karta(self.tresc)
        karta.pack(fill="both", expand=True)
        self.tabela = Tabela(karta, KOLUMNY_TRANSAKCJI, po_dwukliku=self.edytuj)
        self.tabela.pack(fill="both", expand=True, padx=10, pady=10)

    def _buduj_filtry(self) -> None:
        """Tworzy rząd filtrów."""
        rzad = ctk.CTkFrame(self.tresc, fg_color=styl.PRZEZROCZYSTY)
        rzad.pack(fill="x", pady=(0, 12))
        self.fraza = self._pole(rzad, "szukaj w opisie", 170)
        self.od = self._pole(rzad, "od dnia", 95)
        self.do = self._pole(rzad, "do dnia", 95)
        self.konto = self._lista(rzad)
        self.kategoria = self._lista(rzad)
        przycisk(rzad, "Wyczyść", self.wyczysc_filtry).pack(side="left")

    def _pole(self, rzad: Any, podpowiedz: str, szerokosc: int) -> ctk.CTkEntry:
        """Tworzy pole tekstowe filtru, które działa po Enterze i w trakcie pisania."""
        pole = ctk.CTkEntry(
            rzad,
            placeholder_text=podpowiedz,
            width=szerokosc,
            height=34,
            font=styl.czcionka(),
            fg_color=styl.KARTA,
            border_color=styl.RAMKA,
            border_width=1,
            text_color=styl.TEKST,
            placeholder_text_color=styl.TEKST_DRUGI,
        )
        pole.pack(side="left", padx=(0, 8))
        zdarzenie = "<KeyRelease>" if podpowiedz.startswith("szukaj") else "<Return>"
        pole.bind(zdarzenie, lambda _: self.odswiez())
        return pole

    def _lista(self, rzad: Any) -> ctk.CTkOptionMenu:
        """Tworzy rozwijaną listę filtru."""
        lista = ctk.CTkOptionMenu(
            rzad,
            values=[WSZYSTKIE],
            width=130,
            height=34,
            font=styl.czcionka(),
            dropdown_font=styl.czcionka(),
            fg_color=styl.KARTA,
            button_color=styl.RAMKA,
            button_hover_color=styl.NAJECHANY,
            text_color=styl.TEKST,
            command=lambda _: self.odswiez(),
        )
        lista.pack(side="left", padx=(0, 8))
        return lista

    def odswiez(self) -> None:
        wybrane = posortuj(self._filtruj())
        self.tabela.wypelnij(wiersze_transakcji(wybrane, self.serwisy))
        self.podsumowanie.configure(
            text=f"Pozycje: {len(wybrane)}    "
            f"Przychody: {formatuj_kwote(suma_przychodow(wybrane))}    "
            f"Wydatki: {formatuj_kwote(suma_wydatkow(wybrane))}"
        )

    def wyczysc_filtry(self) -> None:
        """Usuwa wszystkie filtry."""
        for pole in (self.fraza, self.od, self.do):
            pole.delete(0, "end")
        for lista in (self.konto, self.kategoria):
            lista.set(WSZYSTKIE)
        self.okno.focus_set()
        self.odswiez()

    def _filtruj(self) -> list[Transakcja]:
        """Zwraca transakcje pasujące do filtrów."""
        konta = {nazwa: numer for numer, nazwa in self.serwisy.konta.nazwy().items()}
        kategorie = {nazwa: numer for numer, nazwa in self.serwisy.kategorie.nazwy().items()}
        for lista, nazwy in ((self.konto, konta), (self.kategoria, kategorie)):
            lista.configure(values=[WSZYSTKIE, *nazwy])
            if lista.get() not in nazwy:
                lista.set(WSZYSTKIE)
        daty = [
            parsuj_date(pole.get()) if pole.get().strip() else None for pole in (self.od, self.do)
        ]
        return self.serwisy.transakcje.filtruj(
            *daty,
            konto_id=konta.get(self.konto.get()),
            kategoria_id=kategorie.get(self.kategoria.get()),
            fraza=self.fraza.get().strip(),
        )

    def edytuj(self) -> None:
        """Otwiera formularz zaznaczonej transakcji."""
        formularze.edycja(self.okno, self._zaznaczona())

    def usun(self) -> None:
        """Usuwa zaznaczoną transakcję po potwierdzeniu."""
        transakcja = self._zaznaczona()
        if self.okno.zapytaj(f"Usunąć „{transakcja.opis}”?"):
            self.serwisy.transakcje.usun(transakcja)
            self.okno.powiadom("Usunięto transakcję.")
            self.odswiez()

    def _zaznaczona(self) -> Transakcja:
        """Zwraca zaznaczoną transakcję."""
        numer = self.tabela.zaznaczony()
        if numer is None:
            raise NieZnalezionoRekordu("Najpierw zaznacz transakcję na liście.")
        return self.serwisy.transakcje.pobierz(numer)
