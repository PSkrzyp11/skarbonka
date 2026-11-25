"""Główne okno aplikacji: pasek boczny, widoki, panel i powiadomienia."""

import logging
import sys
from dataclasses import replace
from types import TracebackType
from typing import Any

import customtkinter as ctk

from skarbonka.config import NAZWA_APLIKACJI, PLIK_IKONY
from skarbonka.gui import styl
from skarbonka.gui.dialog import Powiadomienie, Pytanie
from skarbonka.gui.formularze_transakcji import nowa_transakcja
from skarbonka.gui.pasek_boczny import PasekBoczny
from skarbonka.gui.skladniki import ramka
from skarbonka.gui.widok import Widok
from skarbonka.gui.widok_analizy import WidokAnalizy
from skarbonka.gui.widok_dane import WidokDane
from skarbonka.gui.widok_plan import WidokPlan
from skarbonka.gui.widok_pulpit import WidokPulpit
from skarbonka.gui.widok_stale import WidokStale
from skarbonka.gui.widok_transakcje import WidokTransakcje
from skarbonka.gui.widok_ustawienia import WidokUstawienia
from skarbonka.models.transakcja import Wydatek
from skarbonka.services.uwagi import zbierz_uwagi
from skarbonka.services.zestaw import Serwisy
from skarbonka.wyjatki import BladSkarbonki

logger = logging.getLogger(__name__)

WIDOKI: tuple[type[Widok], ...] = (
    WidokPulpit,
    WidokTransakcje,
    WidokStale,
    WidokPlan,
    WidokAnalizy,
    WidokDane,
    WidokUstawienia,
)


class Okno(ctk.CTk):
    """Okno z paskiem bocznym po lewej i widokiem po prawej."""

    def __init__(self, serwisy: Serwisy) -> None:
        styl.ustaw_motyw(serwisy.ustawienia.wczytaj().motyw)
        super().__init__(fg_color=styl.TLO)
        self.serwisy = serwisy
        self.title(NAZWA_APLIKACJI)
        self.geometry("1300x840")
        self.minsize(1080, 740)
        if sys.platform == "win32" and PLIK_IKONY.exists():
            self.iconbitmap(str(PLIK_IKONY))

        self.panel: Any = None
        self._powiadomienie: Powiadomienie | None = None
        self._widoki: dict[str, Widok] = {}
        self._biezacy = ""
        self.pasek = PasekBoczny(
            self, [(w.IKONA, w.TYTUL) for w in WIDOKI], self.pokaz_widok, self.zmien_motyw
        )
        self.pasek.pack(side="left", fill="y")
        self._miejsce = ramka(self)
        self._miejsce.pack(side="left", fill="both", expand=True)
        self._ustaw_skroty()
        self.pokaz_widok(WIDOKI[0].TYTUL)
        self.after(50, lambda: styl.pomaluj_pasek_tytulu(self))

    def _ustaw_skroty(self) -> None:
        """Ustawia skróty klawiszowe."""
        self.bind("<Control-n>", lambda _: nowa_transakcja(self, Wydatek))
        self.bind("<Escape>", lambda _: self.zamknij_panel())
        self.bind("<Return>", lambda _: self._zatwierdz_panel())
        for numer, klasa in enumerate(WIDOKI, start=1):
            self.bind(f"<Control-Key-{numer}>", lambda _, t=klasa.TYTUL: self.pokaz_widok(t))

    def pokaz_widok(self, tytul: str) -> None:
        """Przełącza na widok o podanym tytule. Widok powstaje przy pierwszym użyciu."""
        self.zamknij_panel()
        if self._biezacy:
            self._widoki[self._biezacy].pack_forget()
        if tytul not in self._widoki:
            klasa = next(k for k in WIDOKI if k.TYTUL == tytul)
            self._widoki[tytul] = klasa(self._miejsce, self)
        self._biezacy = tytul
        self.pasek.wybierz(tytul)
        self._widoki[tytul].pack(fill="both", expand=True)
        self.odswiez()

    def widok(self) -> Widok:
        """Zwraca widok, który jest teraz na ekranie."""
        return self._widoki[self._biezacy]

    def odswiez(self) -> None:
        """Wczytuje aktualne dane do bieżącego widoku."""
        self.widok().odswiez()
        uwagi = zbierz_uwagi(self.serwisy)
        for dzial in (WidokStale.TYTUL, WidokPlan.TYTUL):
            liczba = sum(uwaga.ile for uwaga in uwagi if uwaga.dzial == dzial)
            self.pasek.ustaw_licznik(dzial, liczba)

    def otworz_panel(self, panel: Any) -> None:
        """Zapamiętuje wysunięty panel i zamyka poprzedni."""
        self.zamknij_panel()
        self.panel = panel

    def zamknij_panel(self) -> None:
        """Zamyka wysunięty panel, jeśli jakiś jest otwarty."""
        if self.panel is not None:
            self.panel.destroy()

    def zamknieto_panel(self, panel: Any) -> None:
        """Przyjmuje informację, że panel się zamknął."""
        if self.panel is panel:
            self.panel = None

    def _zatwierdz_panel(self) -> None:
        """Zapisuje otwarty panel po naciśnięciu Enter."""
        if self.panel is not None:
            self.panel.zatwierdz()

    def zmien_motyw(self) -> None:
        """Przełącza motyw jasny i ciemny oraz zapamiętuje wybór."""
        self.focus_set()
        nowy = "jasny" if styl.czy_ciemny() else "ciemny"
        styl.ustaw_motyw(nowy)
        styl.pomaluj_pasek_tytulu(self)
        ustawienia = self.serwisy.ustawienia
        ustawienia.zapisz(replace(ustawienia.wczytaj(), motyw=nowy))
        self.odswiez()

    def powiadom(self, tekst: str, rodzaj: str = "sukces") -> None:
        """Pokazuje na dole okna krótką wiadomość, która sama znika."""
        if self._powiadomienie is not None:
            self._powiadomienie.destroy()
        self._powiadomienie = Powiadomienie(self, tekst, rodzaj)

    def tekst_powiadomienia(self) -> str:
        """Zwraca ostatnio pokazaną wiadomość."""
        return "" if self._powiadomienie is None else self._powiadomienie.tekst

    def zapytaj(self, tekst: str, tak: str = "Tak", grozne: bool = False) -> bool:
        """Zadaje pytanie i czeka na odpowiedź."""
        return Pytanie(self, tekst, tak, grozne).czekaj()

    def report_callback_exception(
        self, typ: type[BaseException], blad: BaseException, slad: TracebackType | None
    ) -> None:
        """Odbiera każdy błąd z kliknięcia. Okno działa dalej."""
        if isinstance(blad, BladSkarbonki):
            logger.warning("%s: %s", typ.__name__, blad)
            self.powiadom(str(blad), "uwaga")
        else:
            logger.error("Nieoczekiwany błąd w oknie", exc_info=(typ, blad, slad))
            self.powiadom("Nieoczekiwany błąd. Szczegóły są w pliku logów.", "blad")


def uruchom_okno(serwisy: Serwisy) -> None:
    """Pokazuje okno i czeka na jego zamknięcie."""
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(NAZWA_APLIKACJI)
    Okno(serwisy).mainloop()
