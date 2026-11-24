"""Kursy walut z publicznego API Narodowego Banku Polskiego."""

import json
import logging
from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from http.client import HTTPException
from urllib.error import HTTPError
from urllib.request import urlopen

from skarbonka.models.kurs import Kurs
from skarbonka.storage.repozytoria_planu import RepozytoriumKursow
from skarbonka.wyjatki import BladKursu, BrakKursu

logger = logging.getLogger(__name__)

ADRES = "https://api.nbp.pl/api/exchangerates/rates/a/{waluta}/{data}/?format=json"
LIMIT_CZASU = 5
NIE_ZNALEZIONO = 404
DNI_WSTECZ = 7
WALUTY = ("EUR", "USD", "GBP", "CHF", "CZK")


def pobierz_z_nbp(waluta: str, dzien: date) -> Decimal:
    """Zwraca średni kurs z podanego dnia.

    W weekendy i święta NBP nie publikuje kursów, wtedy zgłasza BrakKursu.
    """
    adres = ADRES.format(waluta=waluta.lower(), data=dzien.isoformat())
    try:
        with urlopen(adres, timeout=LIMIT_CZASU) as odpowiedz:
            dane = json.load(odpowiedz)
        return Decimal(str(dane["rates"][0]["mid"]))
    except HTTPError as blad:
        if blad.code == NIE_ZNALEZIONO:
            raise BrakKursu(f"Brak kursu {waluta} z dnia {dzien}.") from blad
        raise BladKursu(f"NBP zgłosił błąd {blad.code}.") from blad
    except (OSError, HTTPException) as blad:
        raise BladKursu("Nie udało się pobrać kursu z NBP. Sprawdź połączenie.") from blad
    except (ValueError, KeyError, IndexError, TypeError, InvalidOperation) as blad:
        raise BladKursu("NBP zwrócił odpowiedź w nieznanym układzie.") from blad


class SerwisWalut:
    """Kursy z bazy, a gdy ich brak – z internetu."""

    def __init__(
        self,
        kursy: RepozytoriumKursow,
        pobierz: Callable[[str, date], Decimal] = pobierz_z_nbp,
    ) -> None:
        self._kursy = kursy
        self._pobierz = pobierz

    def kurs(self, waluta: str, dzien: date) -> Kurs:
        """Zwraca kurs z podanego dnia albo z najbliższego wcześniejszego.

        Bez internetu używa ostatniego kursu zapisanego w bazie, o ile nie
        jest starszy niż tydzień.
        """
        znane = {k.data: k for k in self._kursy.wszystkie() if k.waluta == waluta}
        dni = [dzien - timedelta(days=i) for i in range(DNI_WSTECZ + 1)]
        try:
            return self._szukaj(waluta, dni, znane)
        except BladKursu as blad:
            logger.warning("%s", blad)
            for data in dni:
                if data in znane:
                    return znane[data]
            raise

    def _szukaj(self, waluta: str, dni: list[date], znane: dict[date, Kurs]) -> Kurs:
        """Sprawdza kolejne dni wstecz, najpierw w bazie, potem w NBP."""
        for data in dni:
            if data in znane:
                return znane[data]
            try:
                wartosc = self._pobierz(waluta, data)
            except BrakKursu:
                pass
            else:
                return self._kursy.dodaj(Kurs(waluta, data, wartosc))
        raise BladKursu(f"NBP nie ma kursu {waluta} z ostatnich {DNI_WSTECZ} dni.")
