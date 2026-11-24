"""Repozytoria tabel związanych z planowaniem."""

import sqlite3
from datetime import date
from typing import Any

from skarbonka.models.plan import Budzet
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
