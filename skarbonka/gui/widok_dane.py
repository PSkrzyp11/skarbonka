"""Import, eksport, raporty i kopie zapasowe."""

from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog
from typing import Any

from skarbonka.gui import ikony, styl
from skarbonka.gui.formularz import Formularz, Pole
from skarbonka.gui.lista import Lista, Pozycja
from skarbonka.gui.okno_importu import PanelImportu
from skarbonka.gui.skladniki import Karta, etykieta, kafelek_ikony, przycisk, ramka
from skarbonka.gui.widok import Widok
from skarbonka.services.transakcje import posortuj
from skarbonka.utils.formatowanie import formatuj_miesiac
from skarbonka.utils.walidacja import parsuj_miesiac
from skarbonka.wyjatki import NieZnalezionoRekordu

CSV = [("Plik CSV", "*.csv"), ("Wszystkie pliki", "*.*")]
JSON = [("Kopia JSON", "*.json")]
TXT = [("Plik tekstowy", "*.txt")]
OPISY_KOPII = {"auto": "automatyczna", "przed": "przed przywróceniem"}
OPOZNIENIE = 30


class WidokDane(Widok):
    """Wymiana danych z plikami."""

    TYTUL = "Dane"
    IKONA = ikony.FOLDER

    def buduj(self) -> None:
        self.podtytul.configure(text="Wyciągi z banku, pliki i kopie zapasowe")
        siatka = ramka(self.tresc)
        siatka.pack(fill="both", expand=True)
        siatka.grid_columnconfigure(0, weight=5, uniform="dane")
        siatka.grid_columnconfigure(1, weight=4, uniform="dane")
        siatka.grid_rowconfigure(0, weight=1)
        self._buduj_wymiane(siatka)
        self._buduj_kopie(siatka)

    def _buduj_wymiane(self, siatka: Any) -> None:
        """Tworzy listę operacji na plikach."""
        karta = Karta(siatka, "Pliki")
        karta.grid(row=0, column=0, sticky="nsew")
        wiersze = (
            (
                ikony.POBIERZ,
                "Import wyciągu",
                "Plik CSV z banku, z wykrywaniem duplikatów",
                ("Wybierz plik", self.importuj, "glowny"),
            ),
            (
                ikony.COFNIJ,
                "Cofnij ostatni import",
                "Usuwa wszystko, co wtedy dodano",
                ("Cofnij", self.cofnij, "zwykly"),
            ),
            (
                ikony.WYSLIJ,
                "Eksport transakcji",
                "Plik CSV gotowy do otwarcia w Excelu",
                ("Zapisz", self.eksportuj, "zwykly"),
            ),
            (
                ikony.DOKUMENT,
                "Raport miesiąca",
                "Podsumowanie w pliku tekstowym",
                ("Utwórz", self.raport, "zwykly"),
            ),
        )
        for wiersz in wiersze:
            self._dodaj_operacje(karta, *wiersz)

    def _dodaj_operacje(
        self,
        karta: Karta,
        ikona: str,
        tytul: str,
        opis: str,
        akcja: tuple[str, Callable[[], Any], str],
    ) -> None:
        """Dodaje wiersz z ikoną, opisem i przyciskiem."""
        rzad = ramka(karta)
        rzad.pack(fill="x", padx=20, pady=12)
        kafelek_ikony(rzad, ikona, bok=46).pack(side="left")
        napisy = ramka(rzad)
        napisy.pack(side="left", padx=16)
        etykieta(napisy, tytul, 15, "mocny").pack(anchor="w")
        etykieta(napisy, opis, 12, kolor=styl.TEKST_DRUGI).pack(anchor="w", pady=(2, 0))
        przycisk(rzad, akcja[0], akcja[1], akcja[2], 110).pack(side="right")

    def _buduj_kopie(self, siatka: Any) -> None:
        """Tworzy listę kopii zapasowych."""
        karta = Karta(siatka, "Kopie zapasowe")
        karta.grid(row=0, column=1, sticky="nsew", padx=(20, 0))
        przycisk(karta.gora, "Utwórz kopię", self.utworz_kopie, "zwykly", 110, 34).pack(
            side="right"
        )
        dol = ramka(karta)
        dol.pack(side="bottom", fill="x", padx=20, pady=(4, 18))
        przycisk(dol, "Przywróć zaznaczoną", self.przywroc_zaznaczona, "zwykly").pack(side="left")
        przycisk(dol, "Z pliku", self.przywroc_z_pliku, "cichy", 80).pack(side="left", padx=8)
        self.tabela = Lista(
            karta, lambda: None, pusto=(ikony.ARCHIWUM, "Nie ma jeszcze żadnej kopii.")
        )
        self.tabela.pack(fill="both", expand=True, padx=10, pady=(4, 8))

    def odswiez(self) -> None:
        self._kopie = self.serwisy.kopie.lista()
        pozycje = []
        for numer, plik in enumerate(self._kopie):
            czas = datetime.fromtimestamp(plik.stat().st_mtime)
            rodzaje = [o for klucz, o in OPISY_KOPII.items() if f"-{klucz}-" in plik.name]
            opis = rodzaje[0] if rodzaje else "ręczna"
            rozmiar = f"{plik.stat().st_size / 1024:.0f} KB"
            pozycje.append(
                Pozycja(numer, ikony.ARCHIWUM, f"{czas:%d.%m.%Y, %H:%M}", opis, "", rozmiar)
            )
        self.tabela.wypelnij(pozycje)

    def importuj(self) -> Formularz | None:
        """Wybiera plik, pyta o profil oraz konto i pokazuje podgląd."""
        sciezka = filedialog.askopenfilename(parent=self.okno, filetypes=CSV)
        if not sciezka:
            return None

        def zapisz(dane: dict[str, Any]) -> None:
            podglad = self.serwisy.importer.przygotuj(
                Path(sciezka), dane["profil"], dane["konto"].id
            )
            self.okno.after(OPOZNIENIE, lambda: PanelImportu(self.okno, podglad))

        profile = {p.nazwa: p for p in self.serwisy.profile.wszystkie()}
        pola = [
            Pole("profil", "Układ pliku", wybor=profile),
            Pole("konto", "Konto", wybor={k.nazwa: k for k in self.serwisy.konta.wszystkie()}),
        ]
        return Formularz(self.okno, "Import wyciągu", pola, zapisz, "Dalej")

    def cofnij(self) -> None:
        """Usuwa transakcje z ostatniego importu po potwierdzeniu."""
        ostatni = self.serwisy.importer.ostatni()
        pytanie = (
            f"Usunąć transakcje z importu {ostatni.plik} ({ostatni.utworzono:%d.%m.%Y %H:%M})?"
        )
        if self.okno.zapytaj(pytanie, "Usuń", grozne=True):
            liczba = self.serwisy.importer.cofnij(ostatni)
            self.okno.powiadom(f"Usunięte transakcje: {liczba}")
            self.okno.odswiez()

    def eksportuj(self) -> None:
        """Zapisuje wszystkie transakcje do CSV."""
        transakcje = posortuj(self.serwisy.transakcje.wszystkie(), "od najstarszych")
        if not transakcje:
            raise NieZnalezionoRekordu("Brak transakcji do eksportu.")
        sciezka = self._dokad("transakcje.csv", ".csv", CSV)
        if sciezka is not None:
            self.serwisy.eksporter.zapisz(transakcje, sciezka)
            self.okno.powiadom(f"Zapisane transakcje: {len(transakcje)}")

    def raport(self) -> Formularz:
        """Pyta o miesiąc i zapisuje raport."""

        def zapisz(dane: dict[str, Any]) -> None:
            miesiac = dane["miesiac"]
            sciezka = self._dokad(f"raport-{miesiac:%Y-%m}.txt", ".txt", TXT)
            if sciezka is not None:
                self.serwisy.raporty.zapisz(miesiac, sciezka)
                self.okno.powiadom(f"Zapisano raport za {formatuj_miesiac(miesiac)}.")

        pola = [Pole("miesiac", "Miesiąc", parsuj_miesiac, f"{date.today():%m.%Y}")]
        return Formularz(self.okno, "Raport miesiąca", pola, zapisz, "Wybierz miejsce")

    def _dokad(self, nazwa: str, koncowka: str, typy: list) -> Path | None:
        """Pyta, gdzie zapisać plik."""
        sciezka = filedialog.asksaveasfilename(
            parent=self.okno, initialfile=nazwa, defaultextension=koncowka, filetypes=typy
        )
        return Path(sciezka) if sciezka else None

    def utworz_kopie(self) -> None:
        """Tworzy kopię zapasową."""
        self.serwisy.kopie.utworz()
        self.okno.powiadom("Utworzono kopię zapasową.")
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
        transakcje = self.serwisy.kopie.policz(kopia).get("transakcje", 0)
        pytanie = f"Kopia zawiera transakcje: {transakcje}. Zastąpić nią obecne dane?"
        if self.okno.zapytaj(pytanie, "Przywróć"):
            self.serwisy.kopie.przywroc(kopia)
            self.okno.powiadom("Przywrócono dane z kopii.")
            self.okno.odswiez()
