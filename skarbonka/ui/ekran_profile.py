"""Ekran profili CSV: układy plików z banków."""

from skarbonka.models.importy import ProfilCSV
from skarbonka.ui import widoki
from skarbonka.ui.menu import Ekran, OpcjaMenu
from skarbonka.ui.wejscie import (
    potwierdz,
    wczytaj_liczbe,
    wczytaj_nazwe,
    wczytaj_sciezke,
    wybierz,
)

SEPARATORY = {"średnik (;)": ";", "przecinek (,)": ",", "tabulator": "\t"}
KODOWANIA = {"UTF-8": "utf-8-sig", "Windows-1250": "cp1250"}
MAKS_POMINIETYCH_LINII = 100


class EkranProfili(Ekran):
    """Zarządzanie profilami CSV."""

    TYTUL = "Profile CSV banków"

    def opcje(self) -> list[OpcjaMenu]:
        return [
            OpcjaMenu("Lista profili", self.pokaz),
            OpcjaMenu("Dodaj profil na podstawie pliku", self.dodaj),
            OpcjaMenu("Usuń profil", self.usun),
        ]

    def pokaz(self) -> None:
        """Wypisuje profile i ich kolumny."""
        for profil in self.serwisy.profile.wszystkie():
            print(f"{profil.nazwa}: {', '.join(profil.wymagane_kolumny)}")

    def dodaj(self) -> None:
        """Czyta nagłówki przykładowego pliku i pyta o znaczenie kolumn."""
        nazwa = wczytaj_nazwe("Nazwa profilu", self.serwisy.profile.sprawdz_nazwe)
        sciezka = wczytaj_sciezke("Przykładowy plik CSV")
        separator = SEPARATORY[wybierz("Separator", list(SEPARATORY))]
        kodowanie = KODOWANIA[wybierz("Kodowanie", list(KODOWANIA))]
        pomin = wczytaj_liczbe(
            "Ile linii jest przed nagłówkami", maks=MAKS_POMINIETYCH_LINII, domyslna=0
        )
        profil = ProfilCSV(nazwa, separator, kodowanie, pomin)
        kolumny = self.serwisy.profile.kolumny(sciezka, profil)
        profil.kolumna_data = wybierz("Kolumna z datą", kolumny)
        profil.kolumna_kwota = wybierz("Kolumna z kwotą", kolumny)
        profil.kolumna_opis = wybierz("Kolumna z opisem", kolumny)
        self.serwisy.profile.dodaj(profil)
        widoki.sukces(f"Dodano profil {nazwa}.")

    def usun(self) -> None:
        """Usuwa wybrany profil użytkownika po potwierdzeniu."""
        profil = wybierz("Profil do usunięcia", self.serwisy.profile.wlasne())
        if potwierdz(f"Na pewno usunąć „{profil.nazwa}”?"):
            self.serwisy.profile.usun(profil)
            widoki.sukces("Usunięto.")
