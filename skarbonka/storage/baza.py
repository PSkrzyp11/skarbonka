"""Połączenie z bazą SQLite.

Kwoty są zapisywane w groszach jako liczby całkowite, a daty jako tekst
w formacie RRRR-MM-DD.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from skarbonka.config import PLIK_BAZY
from skarbonka.storage.schemat import BEZ_UNIKALNYCH_NAZW, NOWE_KOLUMNY, SCHEMAT
from skarbonka.wyjatki import BladBazy, UszkodzonaBaza

W_PAMIECI = ":memory:"

PLIKI_POMOCNICZE = ("", "-journal", "-wal", "-shm")


def odloz_uszkodzona(sciezka: Path) -> Path:
    """Zmienia nazwę uszkodzonej bazy i jej plików pomocniczych."""
    znacznik = f"{datetime.now():%Y%m%d-%H%M%S-%f}"
    cel = sciezka.with_name(f"{sciezka.stem}.uszkodzona-{znacznik}{sciezka.suffix}")
    try:
        for koncowka in PLIKI_POMOCNICZE:
            plik = Path(f"{sciezka}{koncowka}")
            if plik.exists():
                plik.rename(f"{cel}{koncowka}")
    except OSError as blad:
        raise BladBazy(f"Nie można przenieść uszkodzonej bazy {sciezka}: {blad}") from blad
    return cel


class Baza:
    """Otwarta baza danych."""

    def __init__(self, sciezka: Path | str = PLIK_BAZY) -> None:
        self.sciezka = sciezka
        self._polaczenie: sqlite3.Connection | None = None
        try:
            self._otworz()
        except (sqlite3.OperationalError, OSError) as blad:
            self.zamknij()
            raise BladBazy(f"Nie można otworzyć bazy {sciezka}: {blad}") from blad
        except sqlite3.DatabaseError as blad:
            self.zamknij()
            raise UszkodzonaBaza(f"Plik {sciezka} jest uszkodzony: {blad}") from blad

    def _otworz(self) -> None:
        """Łączy się z plikiem, sprawdza go i tworzy brakujące tabele."""
        if str(self.sciezka) != W_PAMIECI:
            Path(self.sciezka).parent.mkdir(parents=True, exist_ok=True)
        self._polaczenie = sqlite3.connect(self.sciezka, isolation_level=None)
        self._polaczenie.row_factory = sqlite3.Row
        wynik = self._polaczenie.execute("PRAGMA quick_check").fetchone()[0]
        if wynik != "ok":
            raise sqlite3.DatabaseError(wynik)
        self._polaczenie.executescript(SCHEMAT)
        self._pozwol_powtarzac_nazwy()
        self._dodaj_nowe_kolumny()
        self._polaczenie.execute("PRAGMA foreign_keys = ON")

    def _pozwol_powtarzac_nazwy(self) -> None:
        """Przebudowuje starą tabelę stałych pozycji, w której nazwy były niepowtarzalne.

        Teraz dwie osoby mogą mieć pozycję o tej samej nazwie, np. czynsz.
        """
        zapytanie = "SELECT sql FROM sqlite_master WHERE name = 'cykliczne'"
        if "UNIQUE" in self.zapytaj(zapytanie)[0]["sql"]:
            self._polaczenie.executescript(BEZ_UNIKALNYCH_NAZW)

    def _dodaj_nowe_kolumny(self) -> None:
        """Uzupełnia bazę utworzoną przez starszą wersję aplikacji."""
        for tabela, kolumna, typ in NOWE_KOLUMNY:
            if kolumna not in self.kolumny(tabela):
                self._polaczenie.execute(f"ALTER TABLE {tabela} ADD COLUMN {kolumna} {typ}")

    def zamknij(self) -> None:
        """Zamyka połączenie. Można wywołać wielokrotnie."""
        if self._polaczenie is not None:
            self._polaczenie.close()
            self._polaczenie = None

    def wykonaj(self, sql: str, parametry: tuple | list = ()) -> sqlite3.Cursor:
        """Wykonuje polecenie, zamieniając błędy SQLite na BladBazy."""
        if self._polaczenie is None:
            raise BladBazy("Baza danych jest zamknięta.")
        try:
            return self._polaczenie.execute(sql, parametry)
        except (sqlite3.Error, OverflowError, ValueError) as blad:
            raise BladBazy(f"Błąd bazy danych: {blad}") from blad

    def zapytaj(self, sql: str, parametry: tuple | list = ()) -> list[sqlite3.Row]:
        """Zwraca wszystkie wiersze wyniku zapytania."""
        kursor = self.wykonaj(sql, parametry)
        try:
            return kursor.fetchall()
        except sqlite3.Error as blad:
            raise BladBazy(f"Błąd odczytu bazy danych: {blad}") from blad

    def kolumny(self, tabela: str) -> set[str]:
        """Zwraca nazwy kolumn tabeli."""
        return {wiersz["name"] for wiersz in self.zapytaj(f"PRAGMA table_info({tabela})")}

    def wstaw(self, tabela: str, wiersz: dict[str, Any]) -> int:
        """Dodaje wiersz i zwraca jego numer."""
        kolumny = ", ".join(wiersz)
        znaki = ", ".join("?" for _ in wiersz)
        sql = f"INSERT INTO {tabela} ({kolumny}) VALUES ({znaki})"
        return self.wykonaj(sql, list(wiersz.values())).lastrowid

    @contextmanager
    def transakcja(self) -> Iterator[None]:
        """Wykonuje blok poleceń w całości albo wcale.

        Wywołana wewnątrz innej transakcji dołącza do niej.
        """
        if self._polaczenie is not None and self._polaczenie.in_transaction:
            yield
            return
        self.wykonaj("BEGIN")
        try:
            yield
            self.wykonaj("COMMIT")
        except BaseException:
            if self._polaczenie is not None and self._polaczenie.in_transaction:
                self._polaczenie.execute("ROLLBACK")
            raise
