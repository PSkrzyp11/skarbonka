"""Uniwersalny formularz w panelu wysuwanym z prawej strony okna.

Pola są sprawdzane tymi samymi funkcjami, których używa konsola.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from skarbonka.gui import ikony, styl
from skarbonka.gui.animacje import animuj
from skarbonka.gui.pola import PoleDaty, PoleKafelkow, PoleKwoty, PoleListy, PoleTekstowe
from skarbonka.gui.skladniki import (
    Przewijana,
    etykieta,
    przycisk,
    przycisk_ikony,
    ramka,
    segment,
)
from skarbonka.wyjatki import BladSkarbonki, BladWalidacji, NieZnalezionoRekordu

if TYPE_CHECKING:
    from skarbonka.gui.okno import Okno

SZEROKOSC = 420
SZEROKOSC_TEKSTU = 330


@dataclass
class Pole:
    """Jedno pole formularza.

    Rodzaj to: tekst, kwota, data, lista albo kafelki. Dwa ostatnie wymagają
    słownika z wyborem.
    """

    klucz: str
    etykieta: str
    parser: Callable[[str], Any] = str
    wartosc: str = ""
    wybor: dict[str, Any] | None = None
    po_zmianie: Callable[["Formularz"], None] | None = None
    rodzaj: str = "tekst"


@dataclass
class Przelacznik:
    """Opcje na górze panelu, np. rodzaj transakcji."""

    opcje: dict[str, Callable[[], Any]]
    wybrana: str


class Formularz(ctk.CTkFrame):
    """Panel z polami, przyciskiem zapisu i komunikatami o błędach przy polach."""

    def __init__(
        self,
        okno: "Okno",
        tytul: str,
        pola: list[Pole],
        zapisz: Callable[[dict[str, Any]], None],
        napis_przycisku: str = "Zapisz",
        przelacznik: Przelacznik | None = None,
    ) -> None:
        for pole in pola:
            if pole.wybor is not None and not pole.wybor:
                raise NieZnalezionoRekordu(f"{pole.etykieta} – brak pozycji do wyboru.")
        super().__init__(okno, width=SZEROKOSC, fg_color=styl.KARTA, corner_radius=0)
        self.pack_propagate(False)
        self._okno = okno
        self._zapisz = zapisz
        self._pola = {pole.klucz: pole for pole in pola}
        self._kontrolki: dict[str, Any] = {}
        self._bledy: dict[str, ctk.CTkLabel] = {}

        ctk.CTkFrame(self, width=1, fg_color=styl.LINIA, corner_radius=0).pack(
            side="left", fill="y"
        )
        gora = ramka(self)
        gora.pack(fill="x", padx=28, pady=(26, 10))
        etykieta(gora, tytul, 22, "naglowek").pack(side="left")
        przycisk_ikony(gora, ikony.ZAMKNIJ, self.destroy).pack(side="right")
        if przelacznik is not None:
            self._dodaj_przelacznik(przelacznik)

        dol = ramka(self)
        dol.pack(side="bottom", fill="x", padx=28, pady=(8, 26))
        przycisk(dol, napis_przycisku, self.zatwierdz, "glowny", wysokosc=46).pack(fill="x")
        self._blad_ogolny = etykieta(self, "", 12, kolor=styl.ZLY)
        self._blad_ogolny.configure(wraplength=SZEROKOSC_TEKSTU)
        self._blad_ogolny.pack(side="bottom", anchor="w", padx=28)
        tresc = Przewijana(self, styl.KARTA)
        tresc.pack(fill="both", expand=True, padx=(22, 10))
        for pole in pola:
            self._dodaj_pole(tresc, pole)

        okno.otworz_panel(self)
        animuj(self, SZEROKOSC, 0, self._przesun)
        self._ustaw_kursor()

    def _przesun(self, odleglosc: float) -> None:
        """Ustawia panel w podanej odległości od prawej krawędzi."""
        self.place(relx=1, rely=0, x=odleglosc, anchor="ne", relheight=1)
        self.lift()

    def _dodaj_przelacznik(self, przelacznik: Przelacznik) -> None:
        """Tworzy przełącznik rodzaju formularza."""

        def zmien(nazwa: str) -> None:
            if nazwa != przelacznik.wybrana:
                przelacznik.opcje[nazwa]()

        opcje = segment(self, list(przelacznik.opcje), zmien)
        opcje.set(przelacznik.wybrana)
        opcje.pack(fill="x", padx=28, pady=(0, 10))

    def _dodaj_pole(self, rodzic: Any, pole: Pole) -> None:
        """Tworzy etykietę, kontrolkę i miejsce na błąd."""
        etykieta(rodzic, pole.etykieta, 12, "mocny", styl.TEKST_DRUGI).pack(
            anchor="w", padx=4, pady=(14, 4)
        )
        kontrolka = self._utworz_kontrolke(rodzic, pole)
        if pole.wybor is None:
            kontrolka.set(pole.wartosc)
        elif pole.wartosc in pole.wybor:
            kontrolka.set(pole.wartosc)
        kontrolka.pack(anchor="w", padx=4)
        self._kontrolki[pole.klucz] = kontrolka
        self._bledy[pole.klucz] = etykieta(rodzic, "", 12, kolor=styl.ZLY)

    def _utworz_kontrolke(self, rodzic: Any, pole: Pole) -> Any:
        """Wybiera kontrolkę pasującą do rodzaju pola."""

        def zmieniono() -> None:
            self._zmieniono(pole)

        if pole.wybor is not None:
            klasa = PoleKafelkow if pole.rodzaj == "kafelki" else PoleListy
            return klasa(rodzic, list(pole.wybor), zmieniono)
        if pole.rodzaj == "kwota":
            return PoleKwoty(rodzic, zmieniono)
        if pole.rodzaj == "data":
            return PoleDaty(rodzic, zmieniono)
        return PoleTekstowe(rodzic, zmieniono)

    def _ustaw_kursor(self) -> None:
        """Ustawia kursor w pierwszym polu tekstowym."""
        for kontrolka in self._kontrolki.values():
            if isinstance(kontrolka, PoleTekstowe):
                kontrolka.ustaw_kursor()
                return

    def _zmieniono(self, pole: Pole) -> None:
        """Usuwa komunikat o błędzie i wywołuje dodatkową akcję pola."""
        self._pokaz_blad(pole.klucz, "")
        if pole.po_zmianie is not None:
            pole.po_zmianie(self)

    def wartosc(self, klucz: str) -> str:
        """Zwraca tekst wpisany w polu."""
        return self._kontrolki[klucz].get()

    def ustaw(self, klucz: str, tekst: str) -> None:
        """Zmienia tekst pola."""
        self._kontrolki[klucz].set(tekst)

    def ustaw_jednostke(self, klucz: str, jednostka: str) -> None:
        """Zmienia jednostkę przy polu kwoty."""
        self._kontrolki[klucz].jednostka.configure(text=jednostka)

    def blad_pola(self, klucz: str) -> str:
        """Zwraca komunikat przy polu."""
        return self._bledy[klucz].cget("text")

    def blad_ogolny(self) -> str:
        """Zwraca komunikat nad przyciskiem."""
        return self._blad_ogolny.cget("text")

    def _pokaz_blad(self, klucz: str, tekst: str) -> None:
        """Pokazuje albo chowa komunikat przy polu."""
        napis, kontrolka = self._bledy[klucz], self._kontrolki[klucz]
        napis.configure(text=tekst, wraplength=SZEROKOSC_TEKSTU)
        if isinstance(kontrolka, PoleTekstowe):
            kontrolka.oznacz_blad(bool(tekst))
        if tekst:
            napis.pack(anchor="w", padx=4, pady=(4, 0), after=kontrolka)
        else:
            napis.pack_forget()

    def zatwierdz(self) -> None:
        """Sprawdza pola i zapisuje dane. Przy błędzie panel zostaje otwarty."""
        self._blad_ogolny.configure(text="")
        dane, poprawne = {}, True
        for klucz, pole in self._pola.items():
            tekst = self.wartosc(klucz)
            try:
                dane[klucz] = pole.wybor[tekst] if pole.wybor is not None else pole.parser(tekst)
                self._pokaz_blad(klucz, "")
            except BladWalidacji as blad:
                self._pokaz_blad(klucz, str(blad))
                poprawne = False
        if not poprawne:
            return
        try:
            self._zapisz(dane)
        except BladSkarbonki as blad:
            self._blad_ogolny.configure(text=str(blad))
            return
        if self.winfo_exists():
            self.destroy()
        self._okno.odswiez()

    def destroy(self) -> None:
        """Zamyka panel."""
        self._okno.zamknieto_panel(self)
        super().destroy()
