"""Elementy, z których są zbudowane widoki okna."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from tkinter import ttk
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from skarbonka.gui import styl
from skarbonka.utils.daty import przesun_miesiac
from skarbonka.utils.formatowanie import formatuj_miesiac

if TYPE_CHECKING:
    from matplotlib.figure import Figure

NAJMNIEJ = 160


def przycisk(
    rodzic: Any, tekst: str, akcja: Callable[[], None], glowny: bool = False, szerokosc: int = 0
) -> ctk.CTkButton:
    """Tworzy przycisk: główny jest wypełniony, zwykły ma tylko obramowanie."""
    return ctk.CTkButton(
        rodzic,
        text=tekst,
        command=akcja,
        width=szerokosc,
        height=34,
        corner_radius=8,
        font=styl.czcionka(13, gruba=glowny),
        fg_color=styl.AKCENT if glowny else styl.PRZEZROCZYSTY,
        hover_color=styl.AKCENT_NAJECHANY if glowny else styl.NAJECHANY,
        text_color="#ffffff" if glowny else styl.TEKST,
        border_width=0 if glowny else 1,
        border_color=styl.RAMKA,
    )


def etykieta(
    rodzic: Any,
    tekst: str = "",
    rozmiar: int = 13,
    gruba: bool = False,
    kolor: styl.Kolor = styl.TEKST,
) -> ctk.CTkLabel:
    """Tworzy etykietę wyrównaną do lewej."""
    return ctk.CTkLabel(
        rodzic,
        text=tekst,
        font=styl.czcionka(rozmiar, gruba),
        text_color=kolor,
        anchor="w",
        justify="left",
    )


def wyczysc(ramka: Any) -> None:
    """Usuwa wszystko, co jest w ramce."""
    for element in ramka.winfo_children():
        element.destroy()


def przewijana(
    rodzic: Any, wysokosc: int = 200, szerokosc: int = 200, tlo: styl.Kolor = styl.TLO
) -> ctk.CTkScrollableFrame:
    """Tworzy przewijaną ramkę."""
    return ctk.CTkScrollableFrame(rodzic, fg_color=tlo, height=wysokosc, width=szerokosc)


def pasek_postepu(rodzic: Any, procent: float, kolor: styl.Kolor) -> ctk.CTkProgressBar:
    """Tworzy pasek: 100 procent to pełna długość."""
    pasek = ctk.CTkProgressBar(
        rodzic, height=10, corner_radius=5, progress_color=kolor, fg_color=styl.NAJECHANY
    )
    pasek.set(min(max(procent / 100, 0), 1))
    return pasek


def zakladki(rodzic: Any) -> ctk.CTkTabview:
    """Tworzy zakładki w stylu okna."""
    return ctk.CTkTabview(
        rodzic,
        fg_color=styl.PRZEZROCZYSTY,
        anchor="w",
        segmented_button_fg_color=styl.NAJECHANY,
        segmented_button_selected_color=styl.WYBRANY,
        segmented_button_selected_hover_color=styl.WYBRANY,
        segmented_button_unselected_color=styl.NAJECHANY,
        segmented_button_unselected_hover_color=styl.OBRAMOWANIE,
        segmented_button_font=styl.czcionka(),
        text_color=styl.TEKST,
    )


class Karta(ctk.CTkFrame):
    """Prostokąt z obramowaniem i opcjonalnym tytułem."""

    def __init__(self, rodzic: Any, tytul: str = "") -> None:
        super().__init__(
            rodzic,
            fg_color=styl.KARTA,
            border_color=styl.OBRAMOWANIE,
            border_width=1,
            corner_radius=10,
        )
        if tytul:
            etykieta(self, tytul, 13, gruba=True, kolor=styl.TEKST_DRUGI).pack(
                anchor="w", padx=16, pady=(12, 4)
            )


class Kafelek(Karta):
    """Karta z jedną ważną liczbą."""

    def __init__(self, rodzic: Any, tytul: str) -> None:
        super().__init__(rodzic, tytul)
        self._wartosc = etykieta(self, "-", 22, gruba=True)
        self._wartosc.pack(anchor="w", padx=16, pady=(0, 14))

    def ustaw(self, tekst: str, kolor: styl.Kolor = styl.TEKST) -> None:
        """Zmienia pokazywaną wartość."""
        self._wartosc.configure(text=tekst, text_color=kolor)


@dataclass
class Kolumna:
    """Opis kolumny tabeli."""

    nazwa: str
    szerokosc: int
    do_prawej: bool = False
    rozciagliwa: bool = False


@dataclass
class Wiersz:
    """Wiersz tabeli. Klucze służą do sortowania zamiast wyświetlanego tekstu."""

    id: int
    komorki: tuple[str, ...]
    klucze: tuple[Any, ...] = ()
    kolor: styl.Kolor | None = None


class Tabela(ctk.CTkFrame):
    """Tabela z przewijaniem, zaznaczaniem i sortowaniem po kliknięciu nagłówka."""

    def __init__(
        self,
        rodzic: Any,
        kolumny: list[Kolumna],
        wysokosc: int = 10,
        po_dwukliku: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(rodzic, fg_color=styl.PRZEZROCZYSTY)
        self._kolumny = kolumny
        self._wiersze: list[Wiersz] = []
        self._sortowanie: tuple[int, bool] | None = None
        numery = [str(i) for i in range(len(kolumny))]
        self.drzewo = ttk.Treeview(
            self,
            columns=numery,
            show="headings",
            selectmode="browse",
            height=wysokosc,
            style=styl.STYL_TABELI,
        )
        for i, kolumna in enumerate(kolumny):
            strona = "e" if kolumna.do_prawej else "w"
            self.drzewo.heading(
                str(i), text=kolumna.nazwa, anchor=strona, command=lambda i=i: self._sortuj(i)
            )
            self.drzewo.column(
                str(i),
                width=kolumna.szerokosc,
                minwidth=50,
                anchor=strona,
                stretch=kolumna.rozciagliwa,
            )
        pasek = ctk.CTkScrollbar(self, height=NAJMNIEJ // 4, command=self.drzewo.yview)
        self.drzewo.configure(yscrollcommand=pasek.set)
        pasek.pack(side="right", fill="y", padx=(4, 0))
        self.drzewo.pack(side="left", fill="both", expand=True)
        if po_dwukliku is not None:
            self.drzewo.bind("<Double-1>", lambda zdarzenie: self._dwuklik(po_dwukliku))

    def wypelnij(self, wiersze: list[Wiersz]) -> None:
        """Zastępuje zawartość tabeli."""
        self._wiersze = wiersze
        self._pokaz()

    def zaznaczony(self) -> int | None:
        """Zwraca numer zaznaczonego rekordu albo None."""
        zaznaczenie = self.drzewo.selection()
        return int(zaznaczenie[0]) if zaznaczenie else None

    def zaznacz(self, numer: int) -> None:
        """Zaznacza rekord o podanym numerze."""
        self.drzewo.selection_set(str(numer))

    def komorka(self, numer: int, kolumna: int) -> str:
        """Zwraca tekst komórki w wierszu o podanym numerze rekordu."""
        return next(w.komorki[kolumna] for w in self._wiersze if w.id == numer)

    def liczba(self) -> int:
        """Zwraca liczbę wierszy."""
        return len(self._wiersze)

    def _dwuklik(self, akcja: Callable[[], None]) -> None:
        """Wywołuje akcję tylko wtedy, gdy jest zaznaczony wiersz."""
        if self.zaznaczony() is not None:
            akcja()

    def _sortuj(self, numer: int) -> None:
        """Sortuje po kolumnie, a przy drugim kliknięciu odwraca kolejność."""
        malejaco = self._sortowanie == (numer, False)
        self._sortowanie = (numer, malejaco)
        self._pokaz()

    def _pokaz(self) -> None:
        """Wypisuje wiersze w wybranej kolejności."""
        wiersze = self._wiersze
        if self._sortowanie is not None:
            numer, malejaco = self._sortowanie
            wiersze = sorted(
                wiersze, key=lambda w: (w.klucze or w.komorki)[numer], reverse=malejaco
            )
        self.drzewo.delete(*self.drzewo.get_children())
        for wiersz in wiersze:
            znaczniki = ()
            if wiersz.kolor is not None:
                znaczniki = (wiersz.kolor[0],)
                self.drzewo.tag_configure(wiersz.kolor[0], foreground=styl.wybierz(wiersz.kolor))
            self.drzewo.insert(
                "", "end", iid=str(wiersz.id), values=wiersz.komorki, tags=znaczniki
            )


class Wykres(ctk.CTkFrame):
    """Miejsce na wykres albo na napis, gdy nie ma danych."""

    def __init__(self, rodzic: Any) -> None:
        super().__init__(rodzic, fg_color=styl.KARTA)
        self.rysunek: Figure | None = None

    def pokaz(self, rysunek: "Figure") -> None:
        """Osadza rysunek w oknie."""
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        wyczysc(self)
        self.rysunek = rysunek
        plotno = FigureCanvasTkAgg(rysunek, self)
        obszar = plotno.get_tk_widget()
        obszar.configure(
            highlightthickness=0, bg=styl.wybierz(styl.KARTA), width=NAJMNIEJ, height=NAJMNIEJ
        )
        obszar.pack(fill="both", expand=True)
        plotno.draw_idle()

    def pusty(self, tekst: str) -> None:
        """Pokazuje napis zamiast wykresu."""
        wyczysc(self)
        self.rysunek = None
        etykieta(self, tekst, kolor=styl.TEKST_DRUGI).pack(expand=True, pady=40)


class WyborMiesiaca(ctk.CTkFrame):
    """Przełącznik miesięcy ze strzałkami."""

    def __init__(self, rodzic: Any, po_zmianie: Callable[[], None]) -> None:
        super().__init__(rodzic, fg_color=styl.PRZEZROCZYSTY)
        self.miesiac = date.today().replace(day=1)
        self._po_zmianie = po_zmianie
        przycisk(self, "‹", lambda: self.przesun(-1), szerokosc=34).pack(side="left")
        self._napis = ctk.CTkLabel(self, width=150, font=styl.czcionka(14, gruba=True))
        self._napis.pack(side="left", padx=6)
        przycisk(self, "›", lambda: self.przesun(1), szerokosc=34).pack(side="left")
        self._pokaz()

    def przesun(self, ile: int) -> None:
        """Przechodzi o podaną liczbę miesięcy."""
        self.miesiac = przesun_miesiac(self.miesiac, ile)
        self._pokaz()
        self._po_zmianie()

    def _pokaz(self) -> None:
        self._napis.configure(text=formatuj_miesiac(self.miesiac), text_color=styl.TEKST)
