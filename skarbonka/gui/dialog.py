"""Powiadomienia i pytania w stylu okna."""

from typing import TYPE_CHECKING

import customtkinter as ctk

from skarbonka.config import NAZWA_APLIKACJI
from skarbonka.gui import ikony, styl
from skarbonka.gui.animacje import animuj
from skarbonka.gui.pasek_boczny import SZEROKOSC as SZEROKOSC_PASKA
from skarbonka.gui.skladniki import etykieta, kafelek_ikony, przycisk, ramka

if TYPE_CHECKING:
    from skarbonka.gui.okno import Okno

CZAS_POWIADOMIENIA = 5000
WYSOKOSC_WYSUNIECIA = 70
SZEROKOSC_TEKSTU = 340

WYGLAD = {
    "sukces": (ikony.PTASZEK, styl.AKCENT_TLO, styl.AKCENT_TEKST),
    "uwaga": (ikony.OSTRZEZENIE, styl.UWAGA_TLO, styl.UWAGA),
    "blad": (ikony.ZAMKNIJ, styl.ZLY_TLO, styl.ZLY),
}


class Powiadomienie(ctk.CTkFrame):
    """Wiadomość wysuwana z dołu okna. Znika sama albo po kliknięciu."""

    def __init__(self, okno: "Okno", tekst: str, rodzaj: str) -> None:
        super().__init__(
            okno, fg_color=styl.KARTA, border_color=styl.LINIA, border_width=1, corner_radius=14
        )
        self.tekst = tekst
        ikona, tlo, kolor = WYGLAD[rodzaj]
        znak = kafelek_ikony(self, ikona, tlo, kolor, bok=34)
        znak.pack(side="left", padx=(12, 10), pady=12)
        napis = etykieta(self, tekst)
        napis.configure(wraplength=SZEROKOSC_TEKSTU)
        napis.pack(side="left", padx=(0, 18), pady=10)
        for element in (self, znak, napis):
            element.bind("<Button-1>", lambda _: self.destroy())
        animuj(self, WYSOKOSC_WYSUNIECIA, -26, self._przesun)
        self.after(CZAS_POWIADOMIENIA, self.destroy)

    def _przesun(self, odleglosc: float) -> None:
        """Ustawia powiadomienie w podanej odległości od dołu okna."""
        self.place(relx=0.5, rely=1, x=SZEROKOSC_PASKA // 2, y=odleglosc, anchor="s")
        self.lift()


class Pytanie(ctk.CTkToplevel):
    """Małe okno z pytaniem. Odpowiedź jest w polu odpowiedz."""

    def __init__(self, okno: "Okno", tekst: str, tak: str, grozne: bool) -> None:
        super().__init__(okno, fg_color=styl.KARTA)
        self.odpowiedz = False
        self.title(NAZWA_APLIKACJI)
        self.resizable(False, False)
        self.transient(okno)
        srodek = ramka(self)
        srodek.pack(padx=26, pady=24)
        ikona, tlo, kolor = WYGLAD["blad" if grozne else "uwaga"]
        kafelek_ikony(
            srodek, ikony.KOSZ if grozne else ikona, tlo, kolor, bok=44
        ).pack(anchor="w")
        napis = etykieta(srodek, tekst, 14)
        napis.configure(wraplength=SZEROKOSC_TEKSTU)
        napis.pack(anchor="w", pady=(16, 22))
        dol = ramka(srodek)
        dol.pack(fill="x")
        przycisk(dol, tak, self._zgoda, "grozny" if grozne else "glowny", 120).pack(side="right")
        przycisk(dol, "Anuluj", self.destroy, "cichy", 90).pack(side="right", padx=8)
        self.bind("<Return>", lambda _: self._zgoda())
        self.bind("<Escape>", lambda _: self.destroy())
        self._wysrodkuj(okno)

    def _wysrodkuj(self, okno: "Okno") -> None:
        """Ustawia pytanie na środku okna głównego."""
        self.update_idletasks()
        x = okno.winfo_rootx() + (okno.winfo_width() - self.winfo_reqwidth()) // 2
        y = okno.winfo_rooty() + (okno.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{x}+{y}")

    def _zgoda(self) -> None:
        self.odpowiedz = True
        self.destroy()

    def czekaj(self) -> bool:
        """Blokuje okno główne do czasu odpowiedzi."""
        self.wait_visibility()
        self.grab_set()
        self.focus_set()
        self.wait_window()
        return self.odpowiedz
