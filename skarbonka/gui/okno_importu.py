"""Podgląd importu przed zapisaniem transakcji."""

from typing import TYPE_CHECKING

import customtkinter as ctk

from skarbonka.gui import styl
from skarbonka.gui.skladniki import Karta, Tabela, etykieta, przewijana, przycisk
from skarbonka.gui.wiersze import KOLUMNY_TRANSAKCJI, wiersze_transakcji
from skarbonka.models.transakcja import Transakcja
from skarbonka.services.importer import PodgladImportu

if TYPE_CHECKING:
    from skarbonka.gui.okno import Okno

OPOZNIENIE_FOKUSU = 120


class OknoImportu(ctk.CTkToplevel):
    """Pokazuje, co trafi do bazy, i czeka na decyzję."""

    def __init__(self, okno: "Okno", podglad: PodgladImportu) -> None:
        super().__init__(okno, fg_color=styl.TLO)
        self.title("Import wyciągu")
        self.geometry(f"880x600+{okno.winfo_rootx() + 120}+{okno.winfo_rooty() + 60}")
        self.transient(okno)
        self._okno = okno
        self._podglad = podglad
        ramka = ctk.CTkFrame(self, fg_color=styl.PRZEZROCZYSTY)
        ramka.pack(fill="both", expand=True, padx=24, pady=20)
        etykieta(ramka, podglad.plik, 18, gruba=True).pack(anchor="w")
        opis = (
            f"Nowe: {len(podglad.nowe)}, duplikaty: {len(podglad.duplikaty)}, "
            f"błędne: {len(podglad.bledy)}"
        )
        etykieta(ramka, opis, kolor=styl.TEKST_DRUGI).pack(anchor="w", pady=(0, 10))

        dol = ctk.CTkFrame(ramka, fg_color=styl.PRZEZROCZYSTY)
        dol.pack(side="bottom", fill="x", pady=(12, 0))
        self.z_duplikatami = ctk.CTkCheckBox(
            dol,
            text="Dodaj także duplikaty",
            font=styl.czcionka(),
            text_color=styl.TEKST,
            fg_color=styl.AKCENT,
            hover_color=styl.AKCENT_NAJECHANY,
            command=self._pokaz,
        )
        if podglad.duplikaty:
            self.z_duplikatami.pack(side="left")
        self._zapisz = przycisk(dol, "", self.zapisz, glowny=True, szerokosc=140)
        self._zapisz.pack(side="right")
        przycisk(dol, "Anuluj", self.destroy).pack(side="right", padx=8)

        if podglad.bledy:
            bledy = przewijana(ramka, wysokosc=110)
            bledy.pack(side="bottom", fill="x", pady=(10, 0))
            for tekst in podglad.bledy:
                etykieta(bledy, tekst, 12, kolor=styl.ZLY).pack(anchor="w")
        karta = Karta(ramka)
        karta.pack(fill="both", expand=True)
        self.tabela = Tabela(karta, KOLUMNY_TRANSAKCJI)
        self.tabela.pack(fill="both", expand=True, padx=10, pady=10)
        self.bind("<Escape>", lambda _: self.destroy())
        self.after(OPOZNIENIE_FOKUSU, self._przejmij_klawiature)
        self._pokaz()

    def _przejmij_klawiature(self) -> None:
        """Blokuje okno główne."""
        if self.winfo_exists() and self.winfo_viewable():
            self.grab_set()

    def _do_zapisu(self) -> list[Transakcja]:
        """Zwraca transakcje wybrane do zapisania."""
        if self.z_duplikatami.get():
            return self._podglad.nowe + self._podglad.duplikaty
        return self._podglad.nowe

    def _pokaz(self) -> None:
        """Odświeża listę i napis na przycisku."""
        do_zapisu = self._do_zapisu()
        self.tabela.wypelnij(wiersze_transakcji(do_zapisu, self._okno.serwisy))
        self._zapisz.configure(
            text=f"Importuj ({len(do_zapisu)})", state="normal" if do_zapisu else "disabled"
        )

    def zapisz(self) -> None:
        """Zapisuje transakcje i zamyka podgląd."""
        do_zapisu = self._do_zapisu()
        if do_zapisu:
            self._okno.serwisy.importer.zapisz(self._podglad.plik, do_zapisu)
            self._okno.powiadom(f"Zaimportowane transakcje: {len(do_zapisu)}")
        self.destroy()
        self._okno.odswiez()
