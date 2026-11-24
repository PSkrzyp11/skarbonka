"""Repozytoria tabel związanych z planowaniem."""

import sqlite3
from datetime import date
from typing import Any

from skarbonka.models.plan import Budzet, Cel, WplataCelu
from skarbonka.storage.repozytoria import Repozytorium, na_grosze, z_groszy


class RepozytoriumBudzetow(Repozytorium[Budzet]):
    """Tabela budżetów."""

    TABELA = "budzety"

    def _na_wiersz(self, rekord: Budzet) -> dict[str, Any]:
        return {
            "kategoria_id": rekord.kategoria_id,
            "miesiac": rekord.miesiac.isoformat(),
            "grosze": na_grosze(rekord.limit),
        }

    def _z_wiersza(self, wiersz: sqlite3.Row) -> Budzet:
        return Budzet(
            wiersz["kategoria_id"],
            date.fromisoformat(wiersz["miesiac"]),
            z_groszy(wiersz["grosze"]),
            wiersz["id"],
        )


class RepozytoriumCeli(Repozytorium[Cel]):
    """Tabela celów. Suma wpłat jest liczona z osobnej tabeli."""

    TABELA = "cele"

    def _na_wiersz(self, rekord: Cel) -> dict[str, Any]:
        return {
            "nazwa": rekord.nazwa,
            "grosze": na_grosze(rekord.kwota_docelowa),
            "termin": rekord.termin.isoformat(),
        }

    def _z_wiersza(self, wiersz: sqlite3.Row) -> Cel:
        return Cel(
            wiersz["nazwa"],
            z_groszy(wiersz["grosze"]),
            date.fromisoformat(wiersz["termin"]),
            id=wiersz["id"],
        )


class RepozytoriumWplat(Repozytorium[WplataCelu]):
    """Tabela wpłat na cele."""

    TABELA = "wplaty_celu"

    def _na_wiersz(self, rekord: WplataCelu) -> dict[str, Any]:
        return {
            "cel_id": rekord.cel_id,
            "data": rekord.data.isoformat(),
            "grosze": na_grosze(rekord.kwota),
        }

    def _z_wiersza(self, wiersz: sqlite3.Row) -> WplataCelu:
        return WplataCelu(
            wiersz["cel_id"],
            date.fromisoformat(wiersz["data"]),
            z_groszy(wiersz["grosze"]),
            wiersz["id"],
        )
