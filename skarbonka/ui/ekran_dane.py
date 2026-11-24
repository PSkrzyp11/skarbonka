"""Ekran danych: wymiana danych z plikami."""

from datetime import datetime
from pathlib import Path

from skarbonka.models.transakcja import Transakcja
from skarbonka.services.transakcje import posortuj
from skarbonka.ui import widoki
from skarbonka.ui.menu import Ekran, OpcjaMenu
from skarbonka.ui.wejscie import potwierdz, wczytaj_miesiac, wczytaj_sciezke, wybierz

LICZBA_W_PODGLADZIE = 5
LICZBA_KOPII = 10
INNY_PLIK = "inny plik..."


class EkranDanych(Ekran):
    """Import, eksport, raporty i kopie zapasowe."""

    TYTUL = "Dane"

    def opcje(self) -> list[OpcjaMenu]:
        return [
            OpcjaMenu("Import wyciągu CSV", self.importuj),
            OpcjaMenu("Cofnij ostatni import", self.cofnij_import),
            OpcjaMenu("Eksport transakcji do CSV", self.eksportuj),
            OpcjaMenu("Raport miesiąca TXT", self.zapisz_raport),
            OpcjaMenu("Utwórz kopię zapasową", self.utworz_kopie),
            OpcjaMenu("Przywróć kopię zapasową", self.przywroc_kopie),
        ]

    def importuj(self) -> None:
        """Wczytuje plik, pokazuje podgląd i po zgodzie zapisuje transakcje."""
        sciezka = wczytaj_sciezke("Plik CSV")
        profil = wybierz("Profil", self.serwisy.profile.wszystkie())
        konto = wybierz("Konto", self.serwisy.konta.wszystkie())
        podglad = self.serwisy.importer.przygotuj(sciezka, profil, konto.id)
        widoki.pokaz_bledy(podglad.bledy)
        print(
            f"Nowe: {len(podglad.nowe)}, duplikaty: {len(podglad.duplikaty)}, "
            f"błędne: {len(podglad.bledy)}"
        )
        do_zapisu = podglad.nowe
        if podglad.duplikaty:
            self._pokaz_poczatek("Te operacje są już w bazie:", podglad.duplikaty)
            if potwierdz("Zaimportować je mimo to?"):
                do_zapisu = podglad.nowe + podglad.duplikaty
        if not do_zapisu:
            print("Nie ma czego importować.")
            return
        self._pokaz_poczatek("Początek listy do importu:", do_zapisu)
        if potwierdz(f"Zaimportować? (liczba transakcji: {len(do_zapisu)})"):
            self.serwisy.importer.zapisz(podglad.plik, do_zapisu)
            widoki.sukces(f"Zaimportowane transakcje: {len(do_zapisu)}")

    def cofnij_import(self) -> None:
        """Usuwa transakcje z ostatniego importu po potwierdzeniu."""
        ostatni = self.serwisy.importer.ostatni()
        print(f"Ostatni import: {ostatni.plik}, {ostatni.utworzono:%d.%m.%Y %H:%M}")
        if potwierdz("Usunąć wszystkie transakcje z tego importu?"):
            liczba = self.serwisy.importer.cofnij(ostatni)
            widoki.sukces(f"Usunięte transakcje: {liczba}")

    def zapisz_raport(self) -> None:
        """Zapisuje raport wybranego miesiąca."""
        miesiac = wczytaj_miesiac()
        domyslna = self.serwisy.katalog / "raporty" / f"raport-{miesiac:%Y-%m}.txt"
        sciezka = wczytaj_sciezke("Plik docelowy", domyslna)
        if self._mozna_zapisac(sciezka):
            self.serwisy.raporty.zapisz(miesiac, sciezka)
            widoki.sukces(f"Zapisano raport: {sciezka}")

    def utworz_kopie(self) -> None:
        """Zapisuje wszystkie dane do pliku JSON."""
        sciezka = self.serwisy.kopie.utworz()
        widoki.sukces(f"Utworzono kopię: {sciezka}")

    def przywroc_kopie(self) -> None:
        """Zastępuje dane wybraną kopią po potwierdzeniu."""
        kopie = {plik.name: plik for plik in self.serwisy.kopie.lista()[:LICZBA_KOPII]}
        wybor = wybierz("Kopia", [*kopie, INNY_PLIK])
        sciezka = kopie.get(wybor) or wczytaj_sciezke("Plik kopii")
        liczby = self.serwisy.kopie.policz(sciezka)
        print("W kopii:", ", ".join(f"{nazwa} {ile}" for nazwa, ile in liczby.items()))
        if potwierdz("Obecne dane zostaną zastąpione. Kontynuować?"):
            self.serwisy.kopie.przywroc(sciezka)
            widoki.sukces("Przywrócono dane z kopii.")

    def _pokaz_poczatek(self, tytul: str, transakcje: list[Transakcja]) -> None:
        """Wypisuje kilka pierwszych transakcji z listy."""
        print(tytul)
        widoki.pokaz_transakcje(
            transakcje[:LICZBA_W_PODGLADZIE],
            self.serwisy.konta.nazwy(),
            self.serwisy.kategorie.nazwy(),
        )

    def eksportuj(self) -> None:
        """Zapisuje wszystkie transakcje do wybranego pliku."""
        transakcje = posortuj(self.serwisy.transakcje.wszystkie(), "od najstarszych")
        if not transakcje:
            print("Brak transakcji do eksportu.")
            return
        nazwa = f"transakcje-{datetime.now():%Y%m%d-%H%M%S}.csv"
        sciezka = wczytaj_sciezke("Plik docelowy", self.serwisy.katalog / "eksport" / nazwa)
        if self._mozna_zapisac(sciezka):
            self.serwisy.eksporter.zapisz(transakcje, sciezka)
            widoki.sukces(f"Zapisane transakcje: {len(transakcje)}, plik: {sciezka}")

    @staticmethod
    def _mozna_zapisac(sciezka: Path) -> bool:
        """Pyta o zgodę, jeśli plik już istnieje."""
        return not sciezka.exists() or potwierdz("Plik już istnieje. Nadpisać?")
