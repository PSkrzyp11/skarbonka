"""Repozytoria tabel związanych z planowaniem, regułami i kursami."""

import sqlite3
from datetime import date
from decimal import Decimal
from typing import Any

from skarbonka.models.cykliczna import Cykliczna
from skarbonka.models.enums import Czestotliwosc
from skarbonka.models.kategoria import Regula
from skarbonka.models.kurs import Kurs
from skarbonka.models.osoba import Osoba
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


class RepozytoriumOsob(Repozytorium[Osoba]):
    """Tabela osób."""

    TABELA = "osoby"

    def _na_wiersz(self, rekord: Osoba) -> dict[str, Any]:
        return {"nazwa": rekord.nazwa}

    def _z_wiersza(self, wiersz: sqlite3.Row) -> Osoba:
        return Osoba(wiersz["nazwa"], wiersz["id"])


class RepozytoriumCyklicznych(Repozytorium[Cykliczna]):
    """Tabela transakcji cyklicznych."""

    TABELA = "cykliczne"

    def _na_wiersz(self, rekord: Cykliczna) -> dict[str, Any]:
        return {
            "nazwa": rekord.nazwa,
            "rodzaj": rekord.rodzaj,
            "grosze": na_grosze(rekord.kwota),
            "konto_id": rekord.konto_id,
            "kategoria_id": rekord.kategoria_id,
            "start": rekord.start.isoformat(),
            "czestotliwosc": rekord.czestotliwosc.value,
            "ostatnia": rekord.ostatnia.isoformat() if rekord.ostatnia else None,
            "aktywna": int(rekord.aktywna),
            "osoba_id": rekord.osoba_id,
            "zmienna": int(rekord.zmienna),
            "co": rekord.co,
        }

    def _z_wiersza(self, wiersz: sqlite3.Row) -> Cykliczna:
        ostatnia = wiersz["ostatnia"]
        return Cykliczna(
            wiersz["nazwa"],
            wiersz["rodzaj"],
            z_groszy(wiersz["grosze"]),
            wiersz["konto_id"],
            wiersz["kategoria_id"],
            date.fromisoformat(wiersz["start"]),
            Czestotliwosc(wiersz["czestotliwosc"]),
            date.fromisoformat(ostatnia) if ostatnia else None,
            bool(wiersz["aktywna"]),
            wiersz["osoba_id"],
            bool(wiersz["zmienna"]),
            wiersz["co"],
            wiersz["id"],
        )


class RepozytoriumRegul(Repozytorium[Regula]):
    """Tabela reguł kategoryzacji."""

    TABELA = "reguly"

    def _na_wiersz(self, rekord: Regula) -> dict[str, Any]:
        return {
            "fraza": rekord.fraza,
            "kategoria_id": rekord.kategoria_id,
            "priorytet": rekord.priorytet,
        }

    def _z_wiersza(self, wiersz: sqlite3.Row) -> Regula:
        return Regula(
            wiersz["fraza"], wiersz["kategoria_id"], int(wiersz["priorytet"]), wiersz["id"]
        )


class RepozytoriumKursow(Repozytorium[Kurs]):
    """Tabela pobranych kursów walut."""

    TABELA = "kursy"

    def _na_wiersz(self, rekord: Kurs) -> dict[str, Any]:
        return {
            "waluta": rekord.waluta,
            "data": rekord.data.isoformat(),
            "wartosc": str(rekord.wartosc),
        }

    def _z_wiersza(self, wiersz: sqlite3.Row) -> Kurs:
        return Kurs(
            wiersz["waluta"],
            date.fromisoformat(wiersz["data"]),
            Decimal(wiersz["wartosc"]),
            wiersz["id"],
        )
