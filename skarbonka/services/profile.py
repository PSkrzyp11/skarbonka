"""Profile CSV, czyli zapamiętane układy plików z banków."""

from dataclasses import asdict
from pathlib import Path

from skarbonka.models.importy import ProfilCSV
from skarbonka.storage.pliki_csv import czytaj_naglowki
from skarbonka.storage.pliki_json import wczytaj_json, zapisz_json
from skarbonka.utils.walidacja import sprawdz_unikalnosc
from skarbonka.wyjatki import UszkodzonyPlik

PROFIL_SKARBONKI = ProfilCSV(
    "Skarbonka", kolumna_kategoria="kategoria", kolumna_rodzaj="rodzaj"
)


class SerwisProfili:
    """Wbudowany profil i profile użytkownika zapisane w pliku JSON."""

    def __init__(self, plik: Path) -> None:
        self._plik = plik

    def wszystkie(self) -> list[ProfilCSV]:
        """Zwraca profil wbudowany i profile użytkownika."""
        return [PROFIL_SKARBONKI, *self.wlasne()]

    def wlasne(self) -> list[ProfilCSV]:
        """Zwraca profile użytkownika."""
        if not self._plik.exists():
            return []
        try:
            return [ProfilCSV(**pola) for pola in wczytaj_json(self._plik)]
        except TypeError as blad:
            raise UszkodzonyPlik(
                f"Plik profili {self._plik} ma błędną zawartość. Popraw go albo usuń."
            ) from blad

    def kolumny(self, sciezka: Path, profil: ProfilCSV) -> list[str]:
        """Zwraca niepuste nazwy kolumn z podanego pliku."""
        return [kolumna for kolumna in czytaj_naglowki(sciezka, profil) if kolumna]

    def sprawdz_nazwe(self, nazwa: str) -> None:
        """Zgłasza błąd, gdy nazwa jest już zajęta."""
        sprawdz_unikalnosc(nazwa, {p.nazwa for p in self.wszystkie()})

    def dodaj(self, profil: ProfilCSV) -> None:
        """Zapisuje nowy profil."""
        self.sprawdz_nazwe(profil.nazwa)
        self._zapisz([*self.wlasne(), profil])

    def usun(self, profil: ProfilCSV) -> None:
        """Usuwa profil użytkownika."""
        self._zapisz([p for p in self.wlasne() if p.nazwa != profil.nazwa])

    def _zapisz(self, profile: list[ProfilCSV]) -> None:
        """Zapisuje wszystkie profile użytkownika do pliku."""
        zapisz_json(self._plik, [asdict(p) for p in profile])
