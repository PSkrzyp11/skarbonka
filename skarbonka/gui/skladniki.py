"""Elementy, z których są zbudowane widoki okna."""

from collections.abc import Callable
from datetime import date
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from skarbonka.gui import ikony, styl
from skarbonka.gui.animacje import animuj
from skarbonka.utils.daty import przesun_miesiac
from skarbonka.utils.formatowanie import formatuj_miesiac

if TYPE_CHECKING:
    from matplotlib.figure import Figure

NAJMNIEJ = 120
NAJMNIEJSZY_PASEK = 20
WYSOKOSC_PRZYCISKU = 38

WYGLAD_PRZYCISKOW = {
    "glowny": (styl.AKCENT, styl.AKCENT_NAJECHANY, styl.BIALY),
    "zwykly": (styl.WGLEBIENIE, styl.LINIA, styl.TEKST),
    "cichy": (styl.PRZEZROCZYSTY, styl.WGLEBIENIE, styl.TEKST_DRUGI),
    "grozny": (styl.ZLY_TLO, styl.ZLY_TLO, styl.ZLY),
}


def przycisk(
    rodzic: Any,
    tekst: str,
    akcja: Callable[[], Any],
    wyglad: str = "zwykly",
    szerokosc: int = 0,
    wysokosc: int = WYSOKOSC_PRZYCISKU,
) -> ctk.CTkButton:
    """Tworzy przycisk: główny, zwykły, cichy albo groźny."""
    tlo, najechany, kolor = WYGLAD_PRZYCISKOW[wyglad]
    return ctk.CTkButton(
        rodzic,
        text=tekst,
        command=akcja,
        width=szerokosc,
        height=wysokosc,
        corner_radius=9,
        border_spacing=0,
        font=styl.czcionka(13, "mocny"),
        fg_color=tlo,
        hover_color=najechany,
        text_color=kolor,
        cursor="hand2",
    )


def przycisk_ikony(
    rodzic: Any, ikona: str, akcja: Callable[[], Any], wyglad: str = "cichy", bok: int = 36
) -> ctk.CTkButton:
    """Tworzy kwadratowy przycisk z samą ikoną."""
    guzik = przycisk(rodzic, ikona, akcja, wyglad, bok, bok)
    guzik.configure(font=styl.czcionka(15, "ikony"))
    return guzik


def etykieta(
    rodzic: Any,
    tekst: str = "",
    rozmiar: int = 13,
    kroj: str = "tresc",
    kolor: styl.Kolor = styl.TEKST,
) -> ctk.CTkLabel:
    """Tworzy etykietę wyrównaną do lewej."""
    return ctk.CTkLabel(
        rodzic,
        text=tekst,
        font=styl.czcionka(rozmiar, kroj),
        text_color=kolor,
        anchor="w",
        justify="left",
        height=0,
    )


def ramka(rodzic: Any) -> ctk.CTkFrame:
    """Tworzy niewidoczną ramkę do układania elementów."""
    return ctk.CTkFrame(rodzic, fg_color=styl.PRZEZROCZYSTY, width=0, height=0)


class Przewijana(ctk.CTkScrollableFrame):
    """Przewijana ramka, której pasek znika, gdy wszystko się mieści.

    Pasek ma minimalną wysokość, żeby jego pojawienie się nie zmieniało rozmiaru
    ramki. Inaczej pokazywałby się i znikał w nieskończoność.
    """

    def __init__(self, rodzic: Any, tlo: styl.Kolor = styl.TLO) -> None:
        super().__init__(
            rodzic,
            fg_color=tlo,
            corner_radius=0,
            scrollbar_fg_color=tlo,
            scrollbar_button_color=styl.LINIA,
            scrollbar_button_hover_color=styl.RAMKA,
        )
        self._scrollbar.configure(height=NAJMNIEJSZY_PASEK)
        self._czy_pasek = True
        self._parent_canvas.configure(yscrollcommand=self._ustaw_pasek)

    def pokaz(self, element: Any) -> None:
        """Przewija tak, żeby było widać cały element."""
        self.update_idletasks()
        plotno = self._parent_canvas
        brakuje = (
            element.winfo_rooty()
            + element.winfo_height()
            - plotno.winfo_rooty()
            - plotno.winfo_height()
        )
        if brakuje > 0:
            plotno.yview_moveto((plotno.canvasy(0) + brakuje) / self.winfo_height())

    def _ustaw_pasek(self, poczatek: str, koniec: str) -> None:
        """Chowa pasek, gdy nie ma czego przewijać."""
        potrzebny = float(poczatek) > 0 or float(koniec) < 1
        if potrzebny != self._czy_pasek:
            self._czy_pasek = potrzebny
            if potrzebny:
                self._scrollbar.grid()
            else:
                self._scrollbar.grid_remove()
        if potrzebny:
            self._scrollbar.set(poczatek, koniec)


def kafelek_ikony(
    rodzic: Any,
    ikona: str,
    tlo: styl.Kolor = styl.WGLEBIENIE,
    kolor: styl.Kolor = styl.TEKST_DRUGI,
    bok: int = 40,
) -> ctk.CTkLabel:
    """Tworzy ikonę na zaokrąglonym tle."""
    return ctk.CTkLabel(
        rodzic,
        text=ikona,
        width=bok,
        height=bok,
        corner_radius=10,
        fg_color=tlo,
        text_color=kolor,
        font=styl.czcionka(bok * 4 // 9, "ikony"),
    )


def pasek_postepu(
    rodzic: Any, procent: float, kolor: styl.Kolor, tlo: styl.Kolor = styl.WGLEBIENIE
) -> ctk.CTkProgressBar:
    """Tworzy pasek, który płynnie dochodzi do podanego procentu."""
    pasek = ctk.CTkProgressBar(
        rodzic, height=8, width=NAJMNIEJ, corner_radius=4, progress_color=kolor, fg_color=tlo
    )
    animuj(pasek, 0, min(max(procent / 100, 0), 1), pasek.set)
    return pasek


def segment(
    rodzic: Any, wartosci: list[str], po_zmianie: Callable[[str], Any]
) -> ctk.CTkSegmentedButton:
    """Tworzy przełącznik kilku opcji."""
    przelacznik = ctk.CTkSegmentedButton(
        rodzic,
        values=wartosci,
        command=po_zmianie,
        height=36,
        corner_radius=9,
        border_width=3,
        font=styl.czcionka(13, "mocny"),
        fg_color=styl.WGLEBIENIE,
        selected_color=styl.WYBRANY,
        selected_hover_color=styl.WYBRANY,
        unselected_color=styl.WGLEBIENIE,
        unselected_hover_color=styl.LINIA,
        text_color=styl.TEKST,
    )
    przelacznik.set(wartosci[0])
    return przelacznik


def lista_rozwijana(
    rodzic: Any, wartosci: list[str], po_zmianie: Callable[[str], Any], szerokosc: int = 150
) -> ctk.CTkOptionMenu:
    """Tworzy rozwijaną listę w stylu pól tekstowych."""
    return ctk.CTkOptionMenu(
        rodzic,
        values=wartosci,
        command=po_zmianie,
        width=szerokosc,
        height=WYSOKOSC_PRZYCISKU,
        corner_radius=9,
        anchor="w",
        font=styl.czcionka(13),
        dropdown_font=styl.czcionka(13),
        fg_color=styl.WGLEBIENIE,
        button_color=styl.WGLEBIENIE,
        button_hover_color=styl.LINIA,
        text_color=styl.TEKST,
        dropdown_fg_color=styl.KARTA,
        dropdown_hover_color=styl.WGLEBIENIE,
        dropdown_text_color=styl.TEKST,
    )


def pole_tekstowe(rodzic: Any, szerokosc: int = 180, podpowiedz: str = "") -> ctk.CTkEntry:
    """Tworzy pole tekstowe."""
    pole = ctk.CTkEntry(
        rodzic,
        width=szerokosc,
        height=WYSOKOSC_PRZYCISKU,
        corner_radius=9,
        border_width=1,
        placeholder_text=podpowiedz or None,
        font=styl.czcionka(13),
        fg_color=styl.KARTA,
        border_color=styl.RAMKA,
        text_color=styl.TEKST,
        placeholder_text_color=styl.TEKST_DRUGI,
    )
    pole.bind("<FocusIn>", lambda _: pole.configure(border_color=styl.AKCENT_TEKST))
    pole.bind("<FocusOut>", lambda _: pole.configure(border_color=styl.RAMKA))
    return pole


def wyczysc(element: Any) -> None:
    """Usuwa wszystko, co jest w ramce."""
    for dziecko in element.winfo_children():
        dziecko.destroy()


def pusty_stan(
    rodzic: Any, ikona: str, tytul: str, opis: str, akcja: tuple[str, Callable[[], Any]]
) -> ctk.CTkFrame:
    """Tworzy zachętę pokazywaną, gdy nie ma jeszcze danych."""
    miejsce = ramka(rodzic)
    kafelek_ikony(miejsce, ikona, styl.AKCENT_TLO, styl.AKCENT_TEKST, bok=64).pack(pady=(0, 14))
    etykieta(miejsce, tytul, 17, "naglowek").pack()
    etykieta(miejsce, opis, kolor=styl.TEKST_DRUGI).pack(pady=(4, 16))
    przycisk(miejsce, akcja[0], akcja[1], "glowny", 150).pack()
    return miejsce


class Karta(ctk.CTkFrame):
    """Zaokrąglona powierzchnia z opcjonalnym tytułem i miejscem na akcje."""

    def __init__(self, rodzic: Any, tytul: str = "") -> None:
        super().__init__(rodzic, fg_color=styl.KARTA, corner_radius=16)
        self.gora = ramka(self)
        if tytul:
            self.gora.pack(fill="x", padx=20, pady=(16, 6))
            self.tytul = etykieta(self.gora, tytul, 15, "mocny")
            self.tytul.pack(side="left")


class Zakladki(ctk.CTkFrame):
    """Przełącznik stron w obrębie widoku."""

    def __init__(self, rodzic: Any, pasek: Any) -> None:
        super().__init__(rodzic, fg_color=styl.PRZEZROCZYSTY)
        self._pasek = pasek
        self._strony: dict[str, ctk.CTkFrame] = {}
        self._segment: ctk.CTkSegmentedButton | None = None
        self._biezaca = ""

    def add(self, nazwa: str) -> ctk.CTkFrame:
        """Dodaje stronę i zwraca ją do wypełnienia."""
        self._strony[nazwa] = ramka(self)
        return self._strony[nazwa]

    def gotowe(self) -> None:
        """Tworzy przełącznik i pokazuje pierwszą stronę."""
        self._segment = segment(self._pasek, list(self._strony), self.set)
        self._segment.pack(side="left")
        self.set(next(iter(self._strony)))

    def set(self, nazwa: str) -> None:
        """Pokazuje stronę o podanej nazwie."""
        if self._biezaca:
            self._strony[self._biezaca].pack_forget()
        self._biezaca = nazwa
        self._segment.set(nazwa)
        self._strony[nazwa].pack(fill="both", expand=True)

    def get(self) -> str:
        """Zwraca nazwę pokazywanej strony."""
        return self._biezaca


class Wykres(ctk.CTkFrame):
    """Miejsce na wykres albo na napis, gdy nie ma danych."""

    def __init__(self, rodzic: Any, tlo: styl.Kolor = styl.KARTA) -> None:
        super().__init__(rodzic, fg_color=tlo, corner_radius=0)
        self._tlo = tlo
        self.rysunek: Figure | None = None

    def pokaz(self, rysunek: "Figure") -> None:
        """Osadza rysunek w oknie."""
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        wyczysc(self)
        self.rysunek = rysunek
        plotno = FigureCanvasTkAgg(rysunek, self)
        obszar = plotno.get_tk_widget()
        obszar.configure(
            highlightthickness=0, bg=styl.wybierz(self._tlo), width=NAJMNIEJ, height=NAJMNIEJ // 2
        )
        obszar.pack(fill="both", expand=True)
        plotno.draw_idle()

    def pusty(self, tekst: str) -> None:
        """Pokazuje napis zamiast wykresu."""
        wyczysc(self)
        self.rysunek = None
        etykieta(self, tekst, kolor=styl.TEKST_DRUGI).pack(expand=True, pady=20)


class WyborMiesiaca(ctk.CTkFrame):
    """Przełącznik miesięcy ze strzałkami."""

    def __init__(self, rodzic: Any, po_zmianie: Callable[[], None]) -> None:
        super().__init__(rodzic, fg_color=styl.WGLEBIENIE, corner_radius=9)
        self.miesiac = date.today().replace(day=1)
        self._po_zmianie = po_zmianie
        przycisk_ikony(self, ikony.W_LEWO, lambda: self.przesun(-1), bok=32).pack(
            side="left", padx=3, pady=3
        )
        self._napis = ctk.CTkLabel(self, width=140, font=styl.czcionka(13, "mocny"))
        self._napis.pack(side="left")
        przycisk_ikony(self, ikony.W_PRAWO, lambda: self.przesun(1), bok=32).pack(
            side="left", padx=3, pady=3
        )
        self._pokaz()

    def przesun(self, ile: int) -> None:
        """Przechodzi o podaną liczbę miesięcy."""
        self.miesiac = przesun_miesiac(self.miesiac, ile)
        self._pokaz()
        self._po_zmianie()

    def _pokaz(self) -> None:
        self._napis.configure(text=formatuj_miesiac(self.miesiac), text_color=styl.TEKST)
