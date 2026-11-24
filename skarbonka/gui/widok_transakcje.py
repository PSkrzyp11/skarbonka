"""Lista transakcji z filtrami."""

from datetime import date, timedelta

import customtkinter as ctk

from skarbonka.gui import formularze_transakcji as formularze
from skarbonka.gui import ikony, styl
from skarbonka.gui.lista import Lista
from skarbonka.gui.pozycje import pogrupowane_dniami, pozycje_transakcji
from skarbonka.gui.skladniki import (
    Karta,
    etykieta,
    lista_rozwijana,
    przycisk,
    ramka,
)
from skarbonka.gui.widok import Widok
from skarbonka.models.transakcja import Transakcja, Wydatek
from skarbonka.services.transakcje import (
    SORTOWANIA,
    posortuj,
    suma_przychodow,
    suma_wydatkow,
)
from skarbonka.utils.daty import przesun_miesiac
from skarbonka.utils.formatowanie import formatuj_kwote
from skarbonka.wyjatki import NieZnalezionoRekordu

WSZYSTKIE_KONTA = "Wszystkie konta"
WSZYSTKIE_KATEGORIE = "Wszystkie kategorie"
CALY_CZAS = "Cały czas"
SORTOWANIE = "od najnowszych"


def okresy(dzis: date) -> dict[str, tuple[date | None, date | None]]:
    """Zwraca gotowe zakresy dat do wyboru."""
    miesiac = dzis.replace(day=1)
    return {
        CALY_CZAS: (None, None),
        "Ten miesiąc": (miesiac, None),
        "Poprzedni miesiąc": (przesun_miesiac(miesiac, -1), miesiac - timedelta(days=1)),
        "Ostatnie 3 miesiące": (przesun_miesiac(dzis, -3), None),
        "Ten rok": (date(dzis.year, 1, 1), None),
    }


class WidokTransakcje(Widok):
    """Przeglądanie, filtrowanie, dodawanie, edycja i usuwanie."""

    TYTUL = "Transakcje"
    IKONA = ikony.LISTA

    def buduj(self) -> None:
        przycisk(
            self.pasek,
            "Nowa transakcja",
            lambda: formularze.nowa_transakcja(self.okno, Wydatek),
            "glowny",
            160,
            42,
        ).pack()
        self._buduj_filtry()
        karta = Karta(self.tresc)
        karta.pack(fill="both", expand=True)
        self._akcje = ctk.CTkFrame(karta, fg_color=styl.AKCENT_TLO, corner_radius=12)
        self._nazwa_wybranej = etykieta(self._akcje, "", 13, "mocny", styl.AKCENT_TEKST)
        self._nazwa_wybranej.pack(side="left", padx=18)
        przycisk(self._akcje, "Usuń", self.usun, "grozny", 80, 34).pack(
            side="right", padx=8, pady=8
        )
        przycisk(self._akcje, "Edytuj", self.edytuj, "glowny", 80, 34).pack(side="right")
        self.tabela = Lista(
            karta,
            self._wybrano,
            self.edytuj,
            (ikony.LUPA, "Żadna transakcja nie pasuje do filtrów."),
        )
        self.tabela.pack(fill="both", expand=True, padx=10, pady=12)

    def _buduj_filtry(self) -> None:
        """Tworzy wyszukiwarkę i listy filtrów."""
        rzad = ramka(self.tresc)
        rzad.pack(fill="x", pady=(0, 16))
        szukaj = ctk.CTkFrame(rzad, fg_color=styl.KARTA, corner_radius=9, height=38)
        szukaj.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkLabel(
            szukaj,
            text=ikony.LUPA,
            font=styl.czcionka(14, "ikony"),
            text_color=styl.TEKST_DRUGI,
            width=36,
        ).pack(side="left", padx=(4, 0))
        self.fraza = ctk.CTkEntry(
            szukaj,
            placeholder_text="Szukaj w opisach",
            border_width=0,
            width=60,
            fg_color=styl.KARTA,
            font=styl.czcionka(14),
            height=36,
            text_color=styl.TEKST,
            placeholder_text_color=styl.TEKST_DRUGI,
        )
        self.fraza.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.fraza.bind("<KeyRelease>", lambda _: self.odswiez())
        self.okres = self._filtr(rzad, list(okresy(date.today())), 140)
        self.konto = self._filtr(rzad, [WSZYSTKIE_KONTA], 130)
        self.kategoria = self._filtr(rzad, [WSZYSTKIE_KATEGORIE], 150)
        self.kolejnosc = self._filtr(rzad, list(SORTOWANIA), 150)

    def _filtr(self, rzad: ctk.CTkFrame, wartosci: list[str], szerokosc: int) -> ctk.CTkOptionMenu:
        """Tworzy listę filtru."""
        lista = lista_rozwijana(rzad, wartosci, lambda _: self.odswiez(), szerokosc)
        lista.set(wartosci[0])
        lista.pack(side="left", padx=(0, 8))
        return lista

    def odswiez(self) -> None:
        wybrane = posortuj(self._filtruj(), self.kolejnosc.get())
        if self.kolejnosc.get() in ("od najnowszych", "od najstarszych"):
            self.tabela.wypelnij(pogrupowane_dniami(wybrane, self.serwisy))
        else:
            self.tabela.wypelnij(pozycje_transakcji(wybrane, self.serwisy, z_data=True))
        self.podtytul.configure(
            text=f"Pozycje: {len(wybrane)}   ·   "
            f"przychody {formatuj_kwote(suma_przychodow(wybrane))}   ·   "
            f"wydatki {formatuj_kwote(suma_wydatkow(wybrane))}"
        )
        self._wybrano()

    def wyczysc_filtry(self) -> None:
        """Usuwa wszystkie filtry."""
        self.fraza.delete(0, "end")
        self.okres.set(CALY_CZAS)
        self.konto.set(WSZYSTKIE_KONTA)
        self.kategoria.set(WSZYSTKIE_KATEGORIE)
        self.kolejnosc.set(SORTOWANIE)
        self.odswiez()

    def _filtruj(self) -> list[Transakcja]:
        """Zwraca transakcje pasujące do filtrów."""
        konta = {nazwa: numer for numer, nazwa in self.serwisy.konta.nazwy().items()}
        kategorie = {nazwa: numer for numer, nazwa in self.serwisy.kategorie.nazwy().items()}
        for lista, nazwy, wszystkie in (
            (self.konto, konta, WSZYSTKIE_KONTA),
            (self.kategoria, kategorie, WSZYSTKIE_KATEGORIE),
        ):
            lista.configure(values=[wszystkie, *nazwy])
            if lista.get() not in nazwy:
                lista.set(wszystkie)
        od, do = okresy(date.today())[self.okres.get()]
        return self.serwisy.transakcje.filtruj(
            od,
            do,
            konto_id=konta.get(self.konto.get()),
            kategoria_id=kategorie.get(self.kategoria.get()),
            fraza=self.fraza.get().strip(),
        )

    def _wybrano(self) -> None:
        """Pokazuje przyciski dla zaznaczonej transakcji."""
        numer = self.tabela.zaznaczony()
        if numer is None:
            self._akcje.pack_forget()
            return
        self._nazwa_wybranej.configure(text=self.tabela.pozycja(numer).tytul)
        self._akcje.pack(side="bottom", fill="x", padx=12, pady=(0, 12))

    def edytuj(self) -> None:
        """Otwiera panel zaznaczonej transakcji."""
        formularze.edycja(self.okno, self._zaznaczona())

    def usun(self) -> None:
        """Usuwa zaznaczoną transakcję po potwierdzeniu."""
        transakcja = self._zaznaczona()
        if self.okno.zapytaj(f"Usunąć transakcję „{transakcja.opis}”?", "Usuń", grozne=True):
            self.serwisy.transakcje.usun(transakcja)
            self.okno.powiadom("Usunięto transakcję.")
            self.okno.odswiez()

    def _zaznaczona(self) -> Transakcja:
        """Zwraca zaznaczoną transakcję."""
        numer = self.tabela.zaznaczony()
        if numer is None:
            raise NieZnalezionoRekordu("Najpierw zaznacz transakcję na liście.")
        return self.serwisy.transakcje.pobierz(numer)
