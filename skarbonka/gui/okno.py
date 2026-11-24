"""Główne okno aplikacji: pasek boczny i przełączanie widoków."""

import logging
import sys
from dataclasses import replace
from tkinter import messagebox
from types import TracebackType

import customtkinter as ctk

from skarbonka import __version__
from skarbonka.config import NAZWA_APLIKACJI, PLIK_IKONY
from skarbonka.gui import styl
from skarbonka.gui.skladniki import etykieta, przycisk
from skarbonka.gui.widok import Widok
from skarbonka.gui.widok_analizy import WidokAnalizy
from skarbonka.gui.widok_dane import WidokDane
from skarbonka.gui.widok_plan import WidokPlan
from skarbonka.gui.widok_pulpit import WidokPulpit
from skarbonka.gui.widok_transakcje import WidokTransakcje
from skarbonka.gui.widok_ustawienia import WidokUstawienia
from skarbonka.services.zestaw import Serwisy
from skarbonka.wyjatki import BladSkarbonki

logger = logging.getLogger(__name__)

WIDOKI: tuple[type[Widok], ...] = (
    WidokPulpit,
    WidokTransakcje,
    WidokPlan,
    WidokAnalizy,
    WidokDane,
    WidokUstawienia,
)

KOLORY_POWIADOMIEN = {"sukces": styl.DOBRY, "uwaga": styl.UWAGA, "blad": styl.ZLY}
CZAS_POWIADOMIENIA = 6000
SZEROKOSC_PASKA = 210


class Okno(ctk.CTk):
    """Okno z paskiem bocznym po lewej i widokiem po prawej."""

    def __init__(self, serwisy: Serwisy) -> None:
        styl.ustaw_motyw(serwisy.ustawienia.wczytaj().motyw)
        super().__init__(fg_color=styl.TLO)
        self.serwisy = serwisy
        self.title(NAZWA_APLIKACJI)
        self.geometry("1240x800")
        self.minsize(1040, 680)
        if sys.platform == "win32" and PLIK_IKONY.exists():
            self.iconbitmap(str(PLIK_IKONY))
        styl.ustaw_styl_tabel(self)

        self._widoki: dict[str, Widok] = {}
        self._przyciski: dict[str, ctk.CTkButton] = {}
        self._biezacy = ""
        self._czyszczenie: str | None = None
        self._buduj_pasek()
        prawa = ctk.CTkFrame(self, fg_color=styl.PRZEZROCZYSTY, corner_radius=0)
        prawa.pack(side="left", fill="both", expand=True)
        self._powiadomienie = etykieta(prawa, "", 13, gruba=True)
        self._powiadomienie.pack(side="bottom", fill="x", padx=28, pady=(0, 10))
        self._miejsce = ctk.CTkFrame(prawa, fg_color=styl.PRZEZROCZYSTY)
        self._miejsce.pack(side="top", fill="both", expand=True)
        self.pokaz_widok(WIDOKI[0].TYTUL)

    def _buduj_pasek(self) -> None:
        """Tworzy pasek boczny z nawigacją."""
        pasek = ctk.CTkFrame(
            self, width=SZEROKOSC_PASKA, fg_color=styl.PASEK_BOCZNY, corner_radius=0
        )
        pasek.pack(side="left", fill="y")
        pasek.pack_propagate(False)
        etykieta(pasek, NAZWA_APLIKACJI, 22, gruba=True).pack(anchor="w", padx=20, pady=(24, 18))
        for klasa in WIDOKI:
            guzik = ctk.CTkButton(
                pasek,
                text=klasa.TYTUL,
                anchor="w",
                height=40,
                corner_radius=8,
                font=styl.czcionka(14),
                hover_color=styl.NAJECHANY,
                command=lambda tytul=klasa.TYTUL: self.pokaz_widok(tytul),
            )
            guzik.pack(fill="x", padx=12, pady=2)
            self._przyciski[klasa.TYTUL] = guzik
        etykieta(pasek, f"wersja {__version__}", 11, kolor=styl.TEKST_DRUGI).pack(
            side="bottom", anchor="w", padx=20, pady=(4, 16)
        )
        przycisk(pasek, "Zmień motyw", self.zmien_motyw).pack(side="bottom", fill="x", padx=12)

    def pokaz_widok(self, tytul: str) -> None:
        """Przełącza na widok o podanym tytule. Widok powstaje przy pierwszym użyciu."""
        if self._biezacy:
            self._widoki[self._biezacy].pack_forget()
        if tytul not in self._widoki:
            klasa = next(k for k in WIDOKI if k.TYTUL == tytul)
            self._widoki[tytul] = klasa(self._miejsce, self)
        self._biezacy = tytul
        for nazwa, guzik in self._przyciski.items():
            wybrany = nazwa == tytul
            guzik.configure(
                fg_color=styl.AKCENT if wybrany else styl.PRZEZROCZYSTY,
                hover_color=styl.AKCENT_NAJECHANY if wybrany else styl.NAJECHANY,
                text_color="#ffffff" if wybrany else styl.TEKST,
            )
        self._widoki[tytul].pack(fill="both", expand=True)
        self.odswiez()

    def widok(self) -> Widok:
        """Zwraca widok, który jest teraz na ekranie."""
        return self._widoki[self._biezacy]

    def odswiez(self) -> None:
        """Wczytuje aktualne dane do bieżącego widoku."""
        self.widok().odswiez()

    def zmien_motyw(self) -> None:
        """Przełącza motyw jasny i ciemny oraz zapamiętuje wybór."""
        self.focus_set()
        nowy = "jasny" if styl.czy_ciemny() else "ciemny"
        styl.ustaw_motyw(nowy)
        styl.ustaw_styl_tabel(self)
        ustawienia = self.serwisy.ustawienia
        ustawienia.zapisz(replace(ustawienia.wczytaj(), motyw=nowy))
        self.odswiez()

    def powiadom(self, tekst: str, rodzaj: str = "sukces") -> None:
        """Pokazuje na dole okna krótką wiadomość, która sama znika."""
        self._powiadomienie.configure(text=tekst, text_color=KOLORY_POWIADOMIEN[rodzaj])
        if self._czyszczenie is not None:
            self.after_cancel(self._czyszczenie)
        self._czyszczenie = self.after(
            CZAS_POWIADOMIENIA, lambda: self._powiadomienie.configure(text="")
        )

    def tekst_powiadomienia(self) -> str:
        """Zwraca aktualnie pokazywaną wiadomość."""
        return self._powiadomienie.cget("text")

    def zapytaj(self, tekst: str) -> bool:
        """Zadaje pytanie tak/nie."""
        return messagebox.askyesno(NAZWA_APLIKACJI, tekst, parent=self)

    def report_callback_exception(
        self, typ: type[BaseException], blad: BaseException, slad: TracebackType | None
    ) -> None:
        """Odbiera każdy błąd z kliknięcia. Okno działa dalej."""
        if isinstance(blad, BladSkarbonki):
            logger.warning("%s: %s", typ.__name__, blad)
            self.powiadom(str(blad), "blad")
        else:
            logger.error("Nieoczekiwany błąd w oknie", exc_info=(typ, blad, slad))
            self.powiadom("Nieoczekiwany błąd. Szczegóły są w pliku logów.", "blad")


def uruchom_okno(serwisy: Serwisy) -> None:
    """Pokazuje okno i czeka na jego zamknięcie."""
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(NAZWA_APLIKACJI)
    Okno(serwisy).mainloop()
