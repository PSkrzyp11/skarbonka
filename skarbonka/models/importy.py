"""Opis układu pliku CSV z banku."""

from dataclasses import dataclass, fields


@dataclass
class ProfilCSV:
    """Mówi, jak czytać plik CSV: separator, kodowanie i nazwy kolumn."""

    nazwa: str
    separator: str = ";"
    kodowanie: str = "utf-8-sig"
    pomin_linie: int = 0
    kolumna_data: str = "data"
    kolumna_kwota: str = "kwota"
    kolumna_opis: str = "opis"
    kolumna_kategoria: str = ""
    kolumna_rodzaj: str = ""

    def __post_init__(self) -> None:
        """Pilnuje typów pól, bo profil bywa wczytywany z pliku."""
        for pole in fields(self):
            if not isinstance(getattr(self, pole.name), pole.type):
                raise TypeError(f"Pole {pole.name} ma zły typ.")

    @property
    def wymagane_kolumny(self) -> tuple[str, ...]:
        """Zwraca kolumny, bez których nie da się wczytać pliku."""
        return (self.kolumna_data, self.kolumna_kwota, self.kolumna_opis)

    def __str__(self) -> str:
        return self.nazwa
