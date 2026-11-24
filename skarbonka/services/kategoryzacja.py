"""Automatyczne przypisywanie kategorii na podstawie reguł."""

import logging
from dataclasses import replace

from skarbonka.config import KATEGORIE_DOMYSLNE
from skarbonka.models.kategoria import Kategoria, Regula
from skarbonka.models.transakcja import Transakcja
from skarbonka.services.kategorie import SerwisKategorii
from skarbonka.services.transakcje import SerwisTransakcji
from skarbonka.storage.baza import Baza
from skarbonka.storage.repozytoria_planu import RepozytoriumRegul
from skarbonka.wyjatki import BladWalidacji

logger = logging.getLogger(__name__)


class Kategoryzator:
    """Reguły w rodzaju: opis zawiera „biedronka” -> kategoria Jedzenie."""

    def __init__(
        self,
        baza: Baza,
        reguly: RepozytoriumRegul,
        kategorie: SerwisKategorii,
        transakcje: SerwisTransakcji,
    ) -> None:
        self._baza = baza
        self._reguly = reguly
        self._kategorie = kategorie
        self._transakcje = transakcje

    def wszystkie(self) -> list[Regula]:
        """Zwraca reguły od najważniejszej, a przy remisie od najdłuższej frazy."""
        return sorted(
            self._reguly.wszystkie(), key=lambda r: (r.priorytet, len(r.fraza)), reverse=True
        )

    def dodaj(self, fraza: str, kategoria: Kategoria, priorytet: int = 0) -> Regula:
        """Dodaje regułę. Ta sama fraza może wskazywać tylko jedną kategorię danego typu."""
        kategorie = {k.id: k for k in self._kategorie.wszystkie()}
        for regula in self._reguly.wszystkie():
            ten_sam_typ = kategorie[regula.kategoria_id].czy_wydatek == kategoria.czy_wydatek
            if ten_sam_typ and regula.fraza.casefold() == fraza.casefold():
                raise BladWalidacji(f"Reguła dla frazy „{fraza}” już istnieje.")
        return self._reguly.dodaj(Regula(fraza, kategoria.id, priorytet))

    def usun(self, regula: Regula) -> None:
        """Usuwa regułę."""
        self._reguly.usun(regula.id)

    def dopasuj(self, opis: str, rodzaj: type[Transakcja]) -> Kategoria | None:
        """Zwraca kategorię z pierwszej pasującej reguły albo None."""
        pasujace = {k.id: k for k in self._kategorie.pasujace(rodzaj)}
        for regula in self.wszystkie():
            if regula.kategoria_id in pasujace and regula.pasuje(opis):
                return pasujace[regula.kategoria_id]
        return None

    def zastosuj(self) -> int:
        """Przypisuje kategorie transakcjom z kategorii „Inne” i zwraca liczbę zmian."""
        domyslne = {k.id for k in self._kategorie.wszystkie() if k.nazwa in KATEGORIE_DOMYSLNE}
        zmiany = 0
        with self._baza.transakcja():
            for transakcja in self._transakcje.wszystkie():
                if transakcja.kategoria_id not in domyslne:
                    continue
                kategoria = self.dopasuj(transakcja.opis, type(transakcja))
                if kategoria is not None and kategoria.id != transakcja.kategoria_id:
                    self._transakcje.zmien(replace(transakcja, kategoria_id=kategoria.id))
                    zmiany += 1
        logger.info("Reguły zmieniły kategorię %s transakcji", zmiany)
        return zmiany
