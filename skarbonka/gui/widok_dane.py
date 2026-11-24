"""Import, eksport, raporty i kopie zapasowe."""

from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog
from typing import Any

import customtkinter as ctk

from skarbonka.gui import styl
from skarbonka.gui.formularz import Formularz, Pole
from skarbonka.gui.okno_importu import OknoImportu
from skarbonka.gui.skladniki import Karta, Kolumna, Tabela, Wiersz, etykieta, przycisk
from skarbonka.gui.widok import Widok
from skarbonka.services.transakcje import posortuj
from skarbonka.utils.formatowanie import formatuj_date, formatuj_miesiac
from skarbonka.utils.walidacja import parsuj_miesiac
from skarbonka.wyjatki import NieZnalezionoRekordu

CSV = [("Plik CSV", "*.csv"), ("Wszystkie pliki", "*.*")]
JSON = [("Kopia JSON", "*.json")]
TXT = [("Plik tekstowy", "*.txt")]
KOLUMNY_KOPII = [Kolumna("Kopia", 380, rozciagliwa=True), Kolumna("Utworzono", 160)]
OPOZNIENIE = 150


class WidokDane(Widok):
    """Wymiana danych z plikami."""

    TYTUL = "Dane"

    def buduj(self) -> None:
        gora = ctk.CTkFrame(self.tresc, fg_color=styl.PRZEZROCZYSTY)
        gora.pack(fill="x")
        karty = (
            (
                "Import wyciągu bankowego",
                "Wczytuje transakcje z pliku CSV i wykrywa duplikaty.",
                (("Wybierz plik CSV", self.importuj), ("Cofnij ostatni import", self.cofnij)),
            ),
            (
                "Eksport i raport",
                "Zapisuje transakcje do CSV albo podsumowanie miesiąca do TXT.",
                (("Eksport CSV", self.eksportuj), ("Raport TXT", self.raport)),
            ),
        )
        for i, (tytul, opis, akcje) in enumerate(karty):
            karta = Karta(gora, tytul)
            gora.grid_columnconfigure(i, weight=1, uniform="karty")
            karta.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 14, 0))
            etykieta(karta, opis, kolor=styl.TEKST_DRUGI).pack(anchor="w", padx=16)
            self._dodaj_przyciski(karta, akcje)

        kopie = Karta(self.tresc, "Kopie zapasowe")
        kopie.pack(fill="both", expand=True, pady=(14, 0))
        self._dodaj_przyciski(
            kopie,
            (
                ("Utwórz kopię", self.utworz_kopie),
                ("Przywróć zaznaczoną", self.przywroc_zaznaczona),
                ("Przywróć z pliku", self.przywroc_z_pliku),
            ),
        )
        self.tabela = Tabela(kopie, KOLUMNY_KOPII)
        self.tabela.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _dodaj_przyciski(self, karta: Karta, akcje: tuple) -> None:
        """Dodaje rząd przycisków. Pierwszy jest główny."""
        rzad = ctk.CTkFrame(karta, fg_color=styl.PRZEZROCZYSTY)
        rzad.pack(fill="x", padx=16, pady=12)
        for i, (tekst, akcja) in enumerate(akcje):
            przycisk(rzad, tekst, akcja, glowny=i == 0).pack(side="left", padx=(0, 8))

    def odswiez(self) -> None:
        self._kopie = self.serwisy.kopie.lista()
        wiersze = []
        for numer, plik in enumerate(self._kopie):
            czas = datetime.fromtimestamp(plik.stat().st_mtime)
            wiersze.append(Wiersz(numer, (plik.name, f"{czas:%d.%m.%Y %H:%M}"), (plik.name, czas)))
        self.tabela.wypelnij(wiersze)

    def importuj(self) -> Formularz | None:
        """Wybiera plik, pyta o profil oraz konto i pokazuje podgląd."""
        sciezka = filedialog.askopenfilename(parent=self.okno, filetypes=CSV)
        if not sciezka:
            return None

        def zapisz(dane: dict[str, Any]) -> None:
            podglad = self.serwisy.importer.przygotuj(
                Path(sciezka), dane["profil"], dane["konto"].id
            )
            self.okno.after(OPOZNIENIE, lambda: OknoImportu(self.okno, podglad))

        pola = [
            Pole("profil", "Układ pliku", wybor={p.nazwa: p for p in self._profile()}),
            Pole("konto", "Konto", wybor={k.nazwa: k for k in self.serwisy.konta.wszystkie()}),
        ]
        return Formularz(self.okno, "Import wyciągu", pola, zapisz, "Dalej")

    def _profile(self) -> list:
        return self.serwisy.profile.wszystkie()

    def cofnij(self) -> None:
        """Usuwa transakcje z ostatniego importu po potwierdzeniu."""
        ostatni = self.serwisy.importer.ostatni()
        if self.okno.zapytaj(
            f"Usunąć transakcje z importu {ostatni.plik} "
            f"({ostatni.utworzono:%d.%m.%Y %H:%M})?"
        ):
            liczba = self.serwisy.importer.cofnij(ostatni)
            self.okno.powiadom(f"Usunięte transakcje: {liczba}")

    def eksportuj(self) -> None:
        """Zapisuje wszystkie transakcje do CSV."""
        transakcje = posortuj(self.serwisy.transakcje.wszystkie(), "od najstarszych")
        if not transakcje:
            raise NieZnalezionoRekordu("Brak transakcji do eksportu.")
        sciezka = self._dokad("transakcje.csv", ".csv", CSV)
        if sciezka is not None:
            self.serwisy.eksporter.zapisz(transakcje, sciezka)
            self.okno.powiadom(f"Zapisane transakcje: {len(transakcje)}, plik: {sciezka}")

    def raport(self) -> Formularz:
        """Pyta o miesiąc i zapisuje raport."""

        def zapisz(dane: dict[str, Any]) -> None:
            miesiac = dane["miesiac"]
            sciezka = self._dokad(f"raport-{miesiac:%Y-%m}.txt", ".txt", TXT)
            if sciezka is not None:
                self.serwisy.raporty.zapisz(miesiac, sciezka)
                self.okno.powiadom(f"Zapisano raport za {formatuj_miesiac(miesiac)}.")

        pola = [Pole("miesiac", "Miesiąc", parsuj_miesiac, f"{date.today():%m.%Y}")]
        return Formularz(self.okno, "Raport miesiąca", pola, zapisz)

    def _dokad(self, nazwa: str, koncowka: str, typy: list) -> Path | None:
        """Pyta, gdzie zapisać plik."""
        sciezka = filedialog.asksaveasfilename(
            parent=self.okno, initialfile=nazwa, defaultextension=koncowka, filetypes=typy
        )
        return Path(sciezka) if sciezka else None

    def utworz_kopie(self) -> None:
        """Tworzy kopię zapasową."""
        kopia = self.serwisy.kopie.utworz()
        self.okno.powiadom(f"Utworzono kopię z dnia {formatuj_date(date.today())}: {kopia.name}")
        self.odswiez()

    def przywroc_zaznaczona(self) -> None:
        """Przywraca kopię zaznaczoną na liście."""
        numer = self.tabela.zaznaczony()
        if numer is None:
            raise NieZnalezionoRekordu("Najpierw zaznacz kopię na liście.")
        self._przywroc(self._kopie[numer])

    def przywroc_z_pliku(self) -> None:
        """Przywraca kopię z wybranego pliku."""
        sciezka = filedialog.askopenfilename(parent=self.okno, filetypes=JSON)
        if sciezka:
            self._przywroc(Path(sciezka))

    def _przywroc(self, kopia: Path) -> None:
        """Pokazuje zawartość kopii i po zgodzie zastępuje dane."""
        liczby = self.serwisy.kopie.policz(kopia)
        opis = ", ".join(f"{nazwa}: {ile}" for nazwa, ile in liczby.items() if ile)
        if self.okno.zapytaj(f"Kopia zawiera: {opis}. Zastąpić nią obecne dane?"):
            self.serwisy.kopie.przywroc(kopia)
            self.okno.powiadom(f"Przywrócono kopię {kopia.name}.")
            self.odswiez()
