"""Podgląd importu w szerokim panelu, zanim transakcje trafią do bazy."""

from typing import TYPE_CHECKING

import customtkinter as ctk

from skarbonka.gui import ikony, styl
from skarbonka.gui.animacje import animuj
from skarbonka.gui.lista import Lista, Naglowek
from skarbonka.gui.pozycje import pozycje_transakcji
from skarbonka.gui.skladniki import (
    Przewijana,
    etykieta,
    przycisk,
    przycisk_ikony,
    ramka,
)
from skarbonka.models.transakcja import Transakcja
from skarbonka.services.importer import PodgladImportu

if TYPE_CHECKING:
    from skarbonka.gui.okno import Okno

SZEROKOSC = 600


class PanelImportu(ctk.CTkFrame):
    """Pokazuje, co trafi do bazy, i czeka na decyzję."""

    def __init__(self, okno: "Okno", podglad: PodgladImportu) -> None:
        super().__init__(okno, width=SZEROKOSC, fg_color=styl.KARTA, corner_radius=0)
        self._okno = okno
        self._podglad = podglad
        self.pack_propagate(False)
        ctk.CTkFrame(self, width=1, fg_color=styl.LINIA, corner_radius=0).pack(
            side="left", fill="y"
        )
        gora = ramka(self)
        gora.pack(fill="x", padx=28, pady=(26, 2))
        etykieta(gora, "Podgląd importu", 22, "naglowek").pack(side="left")
        przycisk_ikony(gora, ikony.ZAMKNIJ, self.destroy).pack(side="right")
        etykieta(self, podglad.plik, 13, kolor=styl.TEKST_DRUGI).pack(anchor="w", padx=28)
        self._dodaj_liczby()

        self._zapisz = przycisk(self, "", self.zatwierdz, "glowny", wysokosc=46)
        self._zapisz.pack(side="bottom", fill="x", padx=28, pady=(8, 26))
        self.z_duplikatami = ctk.CTkCheckBox(
            self,
            text="Dodaj także duplikaty",
            font=styl.czcionka(13),
            text_color=styl.TEKST,
            fg_color=styl.AKCENT,
            hover_color=styl.AKCENT_NAJECHANY,
            border_color=styl.RAMKA,
            border_width=2,
            command=self._pokaz,
        )
        if podglad.duplikaty:
            self.z_duplikatami.pack(side="bottom", anchor="w", padx=28, pady=8)
        self._dodaj_bledy()
        self.tabela = Lista(self, pusto=(ikony.GOTOWE, "Wszystko z tego pliku jest już w bazie."))
        self.tabela.pack(fill="both", expand=True, padx=16, pady=8)
        self._pokaz()
        okno.otworz_panel(self)
        animuj(self, SZEROKOSC, 0, self._przesun)

    def _przesun(self, odleglosc: float) -> None:
        """Ustawia panel w podanej odległości od prawej krawędzi."""
        self.place(relx=1, rely=0, x=odleglosc, anchor="ne", relheight=1)
        self.lift()

    def _dodaj_liczby(self) -> None:
        """Dodaje rząd liczników."""
        rzad = ramka(self)
        rzad.pack(fill="x", padx=28, pady=(16, 6))
        for nazwa, pozycje, kolor in (
            ("nowe", self._podglad.nowe, styl.AKCENT_TEKST),
            ("duplikaty", self._podglad.duplikaty, styl.UWAGA),
            ("błędne", self._podglad.bledy, styl.ZLY),
        ):
            pole = ramka(rzad)
            pole.pack(side="left", padx=(0, 36))
            etykieta(pole, str(len(pozycje)), 28, "liczby", kolor).pack(anchor="w")
            etykieta(pole, nazwa, 12, kolor=styl.TEKST_DRUGI).pack(anchor="w")

    def _dodaj_bledy(self) -> None:
        """Dodaje listę błędnych linii pliku."""
        if not self._podglad.bledy:
            return
        bledy = Przewijana(self, styl.ZLY_TLO)
        bledy.configure(height=120)
        bledy.pack(side="bottom", fill="x", padx=28, pady=8)
        for tekst in self._podglad.bledy:
            napis = etykieta(bledy, tekst, 12, kolor=styl.ZLY)
            napis.configure(wraplength=SZEROKOSC - 110)
            napis.pack(anchor="w", padx=10, pady=4)

    def _do_zapisu(self) -> list[Transakcja]:
        """Zwraca transakcje wybrane do zapisania."""
        if self.z_duplikatami.get():
            return self._podglad.nowe + self._podglad.duplikaty
        return self._podglad.nowe

    def _pokaz(self) -> None:
        """Odświeża listę i napis na przycisku."""
        do_zapisu = self._do_zapisu()
        pozycje = pozycje_transakcji(do_zapisu, self._okno.serwisy, z_data=True)
        self.tabela.wypelnij([Naglowek("Do zaimportowania"), *pozycje] if pozycje else [])
        self._zapisz.configure(
            text=f"Importuj ({len(do_zapisu)})", state="normal" if do_zapisu else "disabled"
        )

    def zatwierdz(self) -> None:
        """Zapisuje transakcje i zamyka podgląd."""
        do_zapisu = self._do_zapisu()
        if not do_zapisu:
            return
        self._okno.serwisy.importer.zapisz(self._podglad.plik, do_zapisu)
        self.destroy()
        self._okno.powiadom(f"Zaimportowane transakcje: {len(do_zapisu)}")
        self._okno.odswiez()

    def destroy(self) -> None:
        """Zamyka panel."""
        self._okno.zamknieto_panel(self)
        super().destroy()
