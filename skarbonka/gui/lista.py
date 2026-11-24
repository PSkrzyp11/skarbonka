"""Lista rysowana na płótnie: ikony, dwa wiersze tekstu i kwota.

Rysowane są tylko widoczne pozycje, dlatego lista działa płynnie także przy
tysiącach transakcji.
"""

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from tkinter import font
from typing import Any

import customtkinter as ctk

from skarbonka.gui import ikony, styl

WYSOKOSC_POZYCJI = 60
WYSOKOSC_NAGLOWKA = 40
BOK_IKONY = 38
MARGINES = 14
ODSTEP_TEKSTU = 66
PRZERWA = 24
PROMIEN = 18
WIELOKROPEK = "…"


@dataclass
class Pozycja:
    """Jedna pozycja listy."""

    id: int
    ikona: str
    tytul: str
    opis: str = ""
    wartosc: str = ""
    podpis: str = ""
    kolor: styl.Kolor = styl.TEKST
    wyrozniona: bool = False


@dataclass
class Naglowek:
    """Nagłówek grupy, np. dzień z sumą."""

    tekst: str
    wartosc: str = ""


class Lista(ctk.CTkFrame):
    """Przewijana lista z podświetlaniem i zaznaczaniem."""

    def __init__(
        self,
        rodzic: Any,
        po_wyborze: Callable[[], None] | None = None,
        po_dwukliku: Callable[[], None] | None = None,
        pusto: tuple[str, str] = (ikony.ARCHIWUM, "Nic tu jeszcze nie ma."),
        wysokosc: int = 120,
    ) -> None:
        super().__init__(rodzic, fg_color=styl.KARTA, corner_radius=0)
        self._po_wyborze = po_wyborze
        self._pusto = pusto
        self._uklad: list[tuple[int, int, Pozycja | Naglowek]] = []
        self._wybrana: int | None = None
        self._najechana: int | None = None
        self._skala = styl.skala(self)
        self._czcionki = {
            "tytul": self._czcionka("mocny", 14),
            "opis": self._czcionka("tresc", 12),
            "wartosc": self._czcionka("liczby", 16),
            "naglowek": self._czcionka("mocny", 12),
            "ikona": self._czcionka("ikony", 17),
            "duza": self._czcionka("ikony", 30),
        }
        self.plotno = tk.Canvas(
            self,
            highlightthickness=0,
            borderwidth=0,
            height=self._px(wysokosc),
            width=self._px(200),
            yscrollincrement=self._px(WYSOKOSC_POZYCJI // 2),
        )
        self._pasek = ctk.CTkScrollbar(
            self,
            width=12,
            height=40,
            command=self._przewin,
            fg_color=styl.KARTA,
            button_color=styl.LINIA,
            button_hover_color=styl.RAMKA,
        )
        self._wysokosc = 0
        self.plotno.configure(yscrollcommand=self._pasek.set)
        self.plotno.pack(side="left", fill="both", expand=True)
        self.plotno.bind("<Configure>", lambda _: self._zmieniono_rozmiar())
        self.plotno.bind("<Motion>", self._najedz)
        self.plotno.bind("<Leave>", lambda _: self._podswietl(None))
        self.plotno.bind("<Button-1>", self._kliknij)
        self.plotno.bind("<MouseWheel>", self._kolko)
        if po_dwukliku is not None:
            self.plotno.bind("<Double-Button-1>", lambda _: self._dwuklik(po_dwukliku))

    def wypelnij(self, elementy: list[Pozycja | Naglowek]) -> None:
        """Zastępuje zawartość listy. Zaznaczenie zostaje, jeśli pozycja nadal istnieje."""
        self._uklad = []
        y = 0
        for element in elementy:
            wysokosc = WYSOKOSC_POZYCJI if isinstance(element, Pozycja) else WYSOKOSC_NAGLOWKA
            self._uklad.append((y, self._px(wysokosc), element))
            y += self._px(wysokosc)
        self._wysokosc = y
        self.plotno.configure(scrollregion=(0, 0, 1, y))
        if self._wybrana not in {p.id for p in self.pozycje()}:
            self._wybrana = None
        self._najechana = None
        self._zmieniono_rozmiar()

    def pozycje(self) -> list[Pozycja]:
        """Zwraca pozycje bez nagłówków."""
        return [element for _, _, element in self._uklad if isinstance(element, Pozycja)]

    def liczba(self) -> int:
        """Zwraca liczbę pozycji."""
        return len(self.pozycje())

    def zaznaczony(self) -> int | None:
        """Zwraca numer zaznaczonej pozycji albo None."""
        return self._wybrana

    def zaznacz(self, numer: int | None) -> None:
        """Zaznacza pozycję o podanym numerze."""
        self._wybrana = numer
        self._rysuj()
        if self._po_wyborze is not None:
            self._po_wyborze()

    def pozycja(self, numer: int) -> Pozycja:
        """Zwraca pozycję o podanym numerze."""
        return next(p for p in self.pozycje() if p.id == numer)

    def _px(self, wartosc: float) -> int:
        """Przelicza rozmiar na piksele ekranu."""
        return round(wartosc * self._skala)

    def _czcionka(self, kroj: str, rozmiar: int) -> font.Font:
        """Tworzy czcionkę o rozmiarze w pikselach."""
        return font.Font(root=self, family=styl.rodzina(kroj), size=-self._px(rozmiar))

    def _zmieniono_rozmiar(self) -> None:
        """Pokazuje pasek tylko wtedy, gdy jest potrzebny, i rysuje listę."""
        if self._czy_miesci_sie():
            self._pasek.pack_forget()
            self.plotno.yview_moveto(0)
        else:
            self._pasek.pack(side="right", fill="y", before=self.plotno)
        self._rysuj()

    def _czy_miesci_sie(self) -> bool:
        return self._wysokosc <= self.plotno.winfo_height()

    def _przewin(self, *argumenty: str) -> None:
        self.plotno.yview(*argumenty)
        self._rysuj()

    def _kolko(self, zdarzenie: tk.Event) -> None:
        if not self._czy_miesci_sie():
            self.plotno.yview_scroll(-2 if zdarzenie.delta > 0 else 2, "units")
            self._rysuj()
            self._najedz(zdarzenie)

    def _numer_pod(self, zdarzenie: tk.Event) -> int | None:
        """Zwraca numer pozycji pod kursorem."""
        kursor = self.plotno.canvasy(zdarzenie.y)
        for y, wysokosc, element in self._uklad:
            if y <= kursor < y + wysokosc and isinstance(element, Pozycja):
                return element.id
        return None

    def _najedz(self, zdarzenie: tk.Event) -> None:
        self._podswietl(self._numer_pod(zdarzenie))

    def _podswietl(self, numer: int | None) -> None:
        if numer != self._najechana:
            self._najechana = numer
            self.plotno.configure(cursor="hand2" if numer is not None and self._po_wyborze else "")
            self._rysuj()

    def _kliknij(self, zdarzenie: tk.Event) -> None:
        self.plotno.focus_set()
        if self._po_wyborze is not None:
            self.zaznacz(self._numer_pod(zdarzenie))

    def _dwuklik(self, akcja: Callable[[], None]) -> None:
        if self._wybrana is not None:
            akcja()

    def _rysuj(self) -> None:
        """Rysuje widoczną część listy."""
        plotno = self.plotno
        plotno.delete("all")
        plotno.configure(bg=styl.wybierz(styl.KARTA))
        if not self._uklad:
            self._rysuj_pusta()
            return
        gora = plotno.canvasy(0)
        dol = gora + plotno.winfo_height()
        for y, wysokosc, element in self._uklad:
            if y + wysokosc < gora:
                continue
            if y > dol:
                break
            if isinstance(element, Pozycja):
                self._rysuj_pozycje(y, wysokosc, element)
            else:
                self._rysuj_naglowek(y, wysokosc, element)

    def _rysuj_pusta(self) -> None:
        """Rysuje ikonę i napis, gdy lista jest pusta."""
        x, y = self.plotno.winfo_width() // 2, self.plotno.winfo_height() // 2
        kolor = styl.wybierz(styl.TEKST_DRUGI)
        ikona, napis = self._pusto
        self.plotno.create_text(
            x, y - self._px(18), text=ikona, font=self._czcionki["duza"], fill=kolor
        )
        self.plotno.create_text(
            x, y + self._px(18), text=napis, font=self._czcionki["opis"], fill=kolor
        )

    def _rysuj_naglowek(self, y: int, wysokosc: int, naglowek: Naglowek) -> None:
        """Rysuje nagłówek grupy."""
        srodek = y + wysokosc * 0.6
        kolor = styl.wybierz(styl.TEKST_DRUGI)
        self.plotno.create_text(
            self._px(MARGINES),
            srodek,
            text=naglowek.tekst,
            anchor="w",
            font=self._czcionki["naglowek"],
            fill=kolor,
        )
        self.plotno.create_text(
            self._prawa(),
            srodek,
            text=naglowek.wartosc,
            anchor="e",
            font=self._czcionki["opis"],
            fill=kolor,
        )

    def _rysuj_pozycje(self, y: int, wysokosc: int, p: Pozycja) -> None:
        """Rysuje jedną pozycję."""
        czy_wybrana = p.id == self._wybrana
        if czy_wybrana or p.id == self._najechana:
            tlo = styl.AKCENT_TLO if czy_wybrana else styl.NAJECHANY
            self._prostokat(
                self._px(4), y + 2, self.plotno.winfo_width() - self._px(4), y + wysokosc - 2, tlo
            )
        bok = self._px(BOK_IKONY)
        x0, y0 = self._px(MARGINES), y + (wysokosc - bok) // 2
        self._prostokat(
            x0, y0, x0 + bok, y0 + bok, styl.AKCENT_TLO if p.wyrozniona else styl.WGLEBIENIE
        )
        self.plotno.create_text(
            x0 + bok // 2,
            y0 + bok // 2,
            text=p.ikona,
            font=self._czcionki["ikona"],
            fill=styl.wybierz(styl.AKCENT_TEKST if p.wyrozniona else styl.TEKST_DRUGI),
        )
        srodek = y + wysokosc // 2
        gora, dol = srodek - self._px(10), srodek + self._px(11)
        self._napis_z_prawej(p, srodek, gora, dol)
        zajete = max(
            self._czcionki["wartosc"].measure(p.wartosc), self._czcionki["opis"].measure(p.podpis)
        )
        x = self._px(ODSTEP_TEKSTU)
        miejsce = self._prawa() - zajete - self._px(PRZERWA) - x
        for tekst, kroj, kolor, polozenie in (
            (p.tytul, "tytul", styl.TEKST, gora if p.opis else srodek),
            (p.opis, "opis", styl.TEKST_DRUGI, dol),
        ):
            self.plotno.create_text(
                x,
                polozenie,
                text=self._skroc(tekst, kroj, miejsce),
                anchor="w",
                font=self._czcionki[kroj],
                fill=styl.wybierz(kolor),
            )

    def _napis_z_prawej(self, p: Pozycja, srodek: int, gora: int, dol: int) -> None:
        """Rysuje kwotę i podpis pod nią."""
        self.plotno.create_text(
            self._prawa(),
            gora if p.podpis else srodek,
            text=p.wartosc,
            anchor="e",
            font=self._czcionki["wartosc"],
            fill=styl.wybierz(p.kolor),
        )
        self.plotno.create_text(
            self._prawa(),
            dol,
            text=p.podpis,
            anchor="e",
            font=self._czcionki["opis"],
            fill=styl.wybierz(styl.TEKST_DRUGI),
        )

    def _prawa(self) -> int:
        return self.plotno.winfo_width() - self._px(MARGINES + 4)

    def _skroc(self, tekst: str, kroj: str, miejsce: int) -> str:
        """Skraca tekst, który się nie mieści."""
        czcionka = self._czcionki[kroj]
        if czcionka.measure(tekst) <= miejsce:
            return tekst
        while tekst and czcionka.measure(tekst + WIELOKROPEK) > miejsce:
            tekst = tekst[:-1]
        return tekst.rstrip() + WIELOKROPEK

    def _prostokat(self, x0: int, y0: int, x1: int, y1: int, kolor: styl.Kolor) -> None:
        """Rysuje prostokąt z zaokrąglonymi rogami."""
        r = self._px(PROMIEN)
        punkty = [
            *(x0 + r, y0, x0 + r, y0, x1 - r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y0 + r),
            *(x1, y1 - r, x1, y1 - r, x1, y1, x1 - r, y1, x1 - r, y1, x0 + r, y1, x0 + r, y1),
            *(x0, y1, x0, y1 - r, x0, y1 - r, x0, y0 + r, x0, y0 + r, x0, y0),
        ]
        self.plotno.create_polygon(punkty, smooth=True, fill=styl.wybierz(kolor))
