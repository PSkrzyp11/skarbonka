"""Repozytoria: zamiana obiektów na wiersze bazy i z powrotem."""

import sqlite3
from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, ClassVar, Generic, TypeVar

from skarbonka.models.enums import TypKonta
from skarbonka.models.kategoria import Kategoria
from skarbonka.models.importy import Import
from skarbonka.models.konto import Konto
from skarbonka.models.transakcja import Przelew, Przychod, Transakcja, Wydatek
from skarbonka.storage.baza import Baza
from skarbonka.wyjatki import BladBazy, BladSkarbonki, NieZnalezionoRekordu, RekordWUzyciu

T = TypeVar("T")

KLASY_TRANSAKCJI = {klasa.RODZAJ: klasa for klasa in (Wydatek, Przychod, Przelew)}


def na_grosze(kwota: Decimal) -> int:
    """Zamienia złote na grosze."""
    return int((kwota * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def z_groszy(grosze: int) -> Decimal:
    """Zamienia grosze na złote."""
    if not isinstance(grosze, int):
        raise ValueError(f"niepoprawna kwota {grosze}")
    return Decimal(grosze).scaleb(-2)


class Repozytorium(ABC, Generic[T]):
    """Wspólne operacje na jednej tabeli."""

    TABELA: ClassVar[str] = ""

    def __init__(self, baza: Baza) -> None:
        self._baza = baza

    @abstractmethod
    def _na_wiersz(self, rekord: T) -> dict[str, Any]:
        """Zamienia obiekt na wartości kolumn (bez id)."""

    @abstractmethod
    def _z_wiersza(self, wiersz: sqlite3.Row) -> T:
        """Tworzy obiekt z wiersza tabeli."""

    def __len__(self) -> int:
        return self._baza.zapytaj(f"SELECT COUNT(*) FROM {self.TABELA}")[0][0]

    def wszystkie(self) -> list[T]:
        """Zwraca wszystkie obiekty w kolejności dodania."""
        wiersze = self._baza.zapytaj(f"SELECT * FROM {self.TABELA} ORDER BY id")
        return [self._wczytaj(wiersz) for wiersz in wiersze]

    def pobierz(self, numer: int) -> T:
        """Zwraca obiekt o podanym numerze."""
        wiersze = self._baza.zapytaj(f"SELECT * FROM {self.TABELA} WHERE id = ?", (numer,))
        if not wiersze:
            raise NieZnalezionoRekordu(f"Nie ma pozycji o numerze {numer}.")
        return self._wczytaj(wiersze[0])

    def dodaj(self, rekord: T) -> T:
        """Zapisuje obiekt i nadaje mu numer."""
        rekord.id = self._baza.wstaw(self.TABELA, self._na_wiersz(rekord))
        return rekord

    def zmien(self, rekord: T) -> None:
        """Zapisuje nową wersję obiektu o tym samym numerze."""
        wiersz = self._na_wiersz(rekord)
        przypisania = ", ".join(f"{kolumna} = ?" for kolumna in wiersz)
        kursor = self._baza.wykonaj(
            f"UPDATE {self.TABELA} SET {przypisania} WHERE id = ?", [*wiersz.values(), rekord.id]
        )
        self._sprawdz_trafienie(kursor, rekord.id)

    def usun(self, numer: int) -> None:
        """Usuwa obiekt o podanym numerze."""
        try:
            kursor = self._baza.wykonaj(f"DELETE FROM {self.TABELA} WHERE id = ?", (numer,))
        except BladBazy as blad:
            if isinstance(blad.__cause__, sqlite3.IntegrityError):
                raise RekordWUzyciu(
                    "Nie można usunąć pozycji, bo korzystają z niej inne dane."
                ) from blad
            raise
        self._sprawdz_trafienie(kursor, numer)

    def _wczytaj(self, wiersz: sqlite3.Row) -> T:
        """Tworzy obiekt, zgłaszając BladBazy, gdy wiersz ma błędne wartości."""
        try:
            return self._z_wiersza(wiersz)
        except (ValueError, TypeError, KeyError, ArithmeticError, BladSkarbonki) as blad:
            numer = wiersz["id"]
            raise BladBazy(f"Błędne dane w tabeli {self.TABELA}, nr {numer}: {blad}") from blad

    @staticmethod
    def _sprawdz_trafienie(kursor: sqlite3.Cursor, numer: int) -> None:
        """Zgłasza błąd, gdy polecenie nie dotyczyło żadnego wiersza."""
        if kursor.rowcount == 0:
            raise NieZnalezionoRekordu(f"Nie ma pozycji o numerze {numer}.")


class RepozytoriumKont(Repozytorium[Konto]):
    """Tabela kont."""

    TABELA = "konta"

    def _na_wiersz(self, rekord: Konto) -> dict[str, Any]:
        return {
            "nazwa": rekord.nazwa,
            "typ": rekord.typ.value,
            "grosze_poczatkowe": na_grosze(rekord.saldo_poczatkowe),
        }

    def _z_wiersza(self, wiersz: sqlite3.Row) -> Konto:
        return Konto(
            wiersz["nazwa"],
            TypKonta(wiersz["typ"]),
            z_groszy(wiersz["grosze_poczatkowe"]),
            wiersz["id"],
        )


class RepozytoriumKategorii(Repozytorium[Kategoria]):
    """Tabela kategorii."""

    TABELA = "kategorie"

    def _na_wiersz(self, rekord: Kategoria) -> dict[str, Any]:
        return {"nazwa": rekord.nazwa, "czy_wydatek": int(rekord.czy_wydatek)}

    def _z_wiersza(self, wiersz: sqlite3.Row) -> Kategoria:
        return Kategoria(wiersz["nazwa"], bool(wiersz["czy_wydatek"]), wiersz["id"])


class RepozytoriumTransakcji(Repozytorium[Transakcja]):
    """Tabela transakcji wszystkich rodzajów."""

    TABELA = "transakcje"

    def _na_wiersz(self, rekord: Transakcja) -> dict[str, Any]:
        return {
            "rodzaj": rekord.RODZAJ,
            "data": rekord.data.isoformat(),
            "grosze": na_grosze(rekord.kwota),
            "opis": rekord.opis,
            "konto_id": rekord.konto_id,
            "konto_docelowe_id": getattr(rekord, "konto_docelowe_id", None),
            "kategoria_id": rekord.kategoria_id,
            "import_id": rekord.import_id,
            "cykliczna_id": rekord.cykliczna_id,
            "waluta": rekord.waluta,
            "grosze_oryg": None if rekord.kwota_oryg is None else na_grosze(rekord.kwota_oryg),
        }

    def _z_wiersza(self, wiersz: sqlite3.Row) -> Transakcja:
        klasa = KLASY_TRANSAKCJI[wiersz["rodzaj"]]
        grosze_oryg = wiersz["grosze_oryg"]
        pola = {
            "data": date.fromisoformat(wiersz["data"]),
            "kwota": z_groszy(wiersz["grosze"]),
            "opis": wiersz["opis"],
            "konto_id": wiersz["konto_id"],
            "kategoria_id": wiersz["kategoria_id"],
            "id": wiersz["id"],
            "import_id": wiersz["import_id"],
            "cykliczna_id": wiersz["cykliczna_id"],
            "waluta": wiersz["waluta"],
            "kwota_oryg": None if grosze_oryg is None else z_groszy(grosze_oryg),
        }
        if klasa is Przelew:
            pola["konto_docelowe_id"] = wiersz["konto_docelowe_id"]
        return klasa(**pola)

    def usun_z_importu(self, import_id: int) -> int:
        """Usuwa transakcje z jednego importu i zwraca ich liczbę."""
        sql = f"DELETE FROM {self.TABELA} WHERE import_id = ?"
        return self._baza.wykonaj(sql, (import_id,)).rowcount


class RepozytoriumImportow(Repozytorium[Import]):
    """Tabela wykonanych importów."""

    TABELA = "importy"

    def _na_wiersz(self, rekord: Import) -> dict[str, Any]:
        return {"plik": rekord.plik, "utworzono": rekord.utworzono.isoformat(timespec="seconds")}

    def _z_wiersza(self, wiersz: sqlite3.Row) -> Import:
        return Import(wiersz["plik"], datetime.fromisoformat(wiersz["utworzono"]), wiersz["id"])
