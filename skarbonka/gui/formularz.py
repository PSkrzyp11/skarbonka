"""Uniwersalny formularz w osobnym oknie.

Pola są sprawdzane tymi samymi funkcjami, których używa konsola.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from skarbonka.gui import styl
from skarbonka.gui.skladniki import etykieta, przycisk
from skarbonka.wyjatki import BladSkarbonki, BladWalidacji, NieZnalezionoRekordu

if TYPE_CHECKING:
    from skarbonka.gui.okno import Okno

SZEROKOSC = 420
OPOZNIENIE_FOKUSU = 120


@dataclass
class Pole:
    """Jedno pole formularza: tekstowe albo, gdy podano wybór, lista."""

    klucz: str
    etykieta: str
    parser: Callable[[str], Any] = str
    wartosc: str = ""
    wybor: dict[str, Any] | None = None
    po_zmianie: Callable[["Formularz"], None] | None = None


class Formularz(ctk.CTkToplevel):
    """Okno z polami, przyciskiem Zapisz i komunikatami o błędach przy polach."""

    def __init__(
        self,
        okno: "Okno",
        tytul: str,
        pola: list[Pole],
        zapisz: Callable[[dict[str, Any]], None],
        napis_przycisku: str = "Zapisz",
    ) -> None:
        for pole in pola:
            if pole.wybor is not None and not pole.wybor:
                raise NieZnalezionoRekordu(f"{pole.etykieta} – brak pozycji do wyboru.")
        super().__init__(okno, fg_color=styl.TLO)
        self.title(tytul)
        self.resizable(False, False)
        self._okno = okno
        self._zapisz = zapisz
        self._pola = {pole.klucz: pole for pole in pola}
        self._kontrolki: dict[str, Any] = {}
        self._bledy: dict[str, ctk.CTkLabel] = {}

        ramka = ctk.CTkFrame(self, fg_color=styl.PRZEZROCZYSTY)
        ramka.pack(fill="both", expand=True, padx=24, pady=20)
        etykieta(ramka, tytul, 18, gruba=True).pack(anchor="w", pady=(0, 8))
        for pole in pola:
            self._dodaj_pole(ramka, pole)
        self._blad_ogolny = etykieta(ramka, "", 12, kolor=styl.ZLY)
        self._blad_ogolny.configure(wraplength=SZEROKOSC - 60)
        self._blad_ogolny.pack(anchor="w", pady=(8, 0))
        self._dodaj_przyciski(ramka, napis_przycisku)
        self._ustaw_okno(okno)

    def _dodaj_pole(self, ramka: Any, pole: Pole) -> None:
        """Tworzy etykietę, kontrolkę i miejsce na błąd."""
        etykieta(ramka, pole.etykieta, 12, kolor=styl.TEKST_DRUGI).pack(anchor="w", pady=(8, 0))
        if pole.wybor is not None:
            kontrolka = ctk.CTkOptionMenu(
                ramka,
                values=list(pole.wybor),
                width=SZEROKOSC - 48,
                height=34,
                font=styl.czcionka(),
                dropdown_font=styl.czcionka(),
                fg_color=styl.KARTA,
                button_color=styl.RAMKA,
                button_hover_color=styl.NAJECHANY,
                text_color=styl.TEKST,
                command=lambda _: self._zmieniono(pole),
            )
            kontrolka.set(pole.wartosc if pole.wartosc in pole.wybor else next(iter(pole.wybor)))
        else:
            kontrolka = ctk.CTkEntry(
                ramka,
                width=SZEROKOSC - 48,
                height=34,
                font=styl.czcionka(),
                fg_color=styl.KARTA,
                border_color=styl.RAMKA,
                border_width=1,
                text_color=styl.TEKST,
            )
            kontrolka.insert(0, pole.wartosc)
            kontrolka.bind("<FocusOut>", lambda _: self._zmieniono(pole))
        kontrolka.pack(anchor="w")
        self._kontrolki[pole.klucz] = kontrolka
        self._bledy[pole.klucz] = etykieta(ramka, "", 11, kolor=styl.ZLY)

    def _dodaj_przyciski(self, ramka: Any, napis: str) -> None:
        """Tworzy przyciski na dole formularza."""
        dol = ctk.CTkFrame(ramka, fg_color=styl.PRZEZROCZYSTY)
        dol.pack(fill="x", pady=(12, 0))
        przycisk(dol, napis, self.zatwierdz, glowny=True, szerokosc=110).pack(side="right")
        przycisk(dol, "Anuluj", self.destroy, szerokosc=90).pack(side="right", padx=8)

    def _ustaw_okno(self, okno: "Okno") -> None:
        """Ustawia formularz na środku okna głównego i przejmuje klawiaturę."""
        self.transient(okno)
        self.update_idletasks()
        x = okno.winfo_rootx() + (okno.winfo_width() - self.winfo_reqwidth()) // 2
        y = okno.winfo_rooty() + (okno.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.bind("<Return>", lambda _: self.zatwierdz())
        self.bind("<Escape>", lambda _: self.destroy())
        self.after(OPOZNIENIE_FOKUSU, self._przejmij_klawiature)

    def _przejmij_klawiature(self) -> None:
        """Blokuje okno główne i ustawia kursor w pierwszym polu."""
        if self.winfo_exists() and self.winfo_viewable():
            self.grab_set()
            next(iter(self._kontrolki.values())).focus_set()

    def _zmieniono(self, pole: Pole) -> None:
        """Wywołuje dodatkową akcję pola, jeśli ją ma."""
        if pole.po_zmianie is not None:
            pole.po_zmianie(self)

    def wartosc(self, klucz: str) -> str:
        """Zwraca tekst wpisany w polu."""
        return self._kontrolki[klucz].get()

    def ustaw(self, klucz: str, tekst: str) -> None:
        """Zmienia tekst pola."""
        kontrolka = self._kontrolki[klucz]
        if isinstance(kontrolka, ctk.CTkOptionMenu):
            kontrolka.set(tekst)
        else:
            kontrolka.delete(0, "end")
            kontrolka.insert(0, tekst)

    def zatwierdz(self) -> None:
        """Sprawdza pola i zapisuje dane. Przy błędzie formularz zostaje otwarty."""
        self._blad_ogolny.configure(text="")
        dane, poprawne = {}, True
        for klucz, pole in self._pola.items():
            self._bledy[klucz].pack_forget()
            tekst = self.wartosc(klucz)
            try:
                dane[klucz] = pole.wybor[tekst] if pole.wybor is not None else pole.parser(tekst)
            except BladWalidacji as blad:
                self._bledy[klucz].configure(text=str(blad), wraplength=SZEROKOSC - 60)
                self._bledy[klucz].pack(anchor="w", after=self._kontrolki[klucz])
                poprawne = False
        if not poprawne:
            return
        try:
            self._zapisz(dane)
        except BladSkarbonki as blad:
            self._blad_ogolny.configure(text=str(blad))
            return
        self.destroy()
        self._okno.odswiez()
