"""Planowanie: budżety miesięczne i cele oszczędnościowe."""

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from skarbonka.models.enums import StanBudzetu
from skarbonka.models.plan import Budzet, Cel, WplataCelu
from skarbonka.models.transakcja import ZERO
from skarbonka.services.analizy import z_miesiaca
from skarbonka.services.kategorie import SerwisKategorii
from skarbonka.services.transakcje import SerwisTransakcji, suma_wydatkow
from skarbonka.services.ustawienia import SerwisUstawien
from skarbonka.storage.repozytoria_planu import (
    RepozytoriumBudzetow,
    RepozytoriumCeli,
    RepozytoriumWplat,
)
from skarbonka.utils.daty import przesun_miesiac
from skarbonka.utils.walidacja import sprawdz_unikalnosc


@dataclass
class WykonanieBudzetu:
    """Budżet zestawiony z tym, co faktycznie wydano."""

    budzet: Budzet
    kategoria: str
    wydano: Decimal
    procent: float
    stan: StanBudzetu


class SerwisBudzetow:
    """Ustawianie i kontrola budżetów."""

    def __init__(
        self,
        budzety: RepozytoriumBudzetow,
        transakcje: SerwisTransakcji,
        kategorie: SerwisKategorii,
        ustawienia: SerwisUstawien,
    ) -> None:
        self._budzety = budzety
        self._transakcje = transakcje
        self._kategorie = kategorie
        self._ustawienia = ustawienia

    def z_miesiaca(self, miesiac: date) -> list[Budzet]:
        """Zwraca budżety podanego miesiąca."""
        poczatek = miesiac.replace(day=1)
        return [b for b in self._budzety.wszystkie() if b.miesiac == poczatek]

    def ustaw(self, kategoria_id: int, miesiac: date, limit: Decimal) -> Budzet:
        """Dodaje budżet albo zmienia limit istniejącego."""
        nowy = Budzet(kategoria_id, miesiac.replace(day=1), limit)
        for obecny in self.z_miesiaca(miesiac):
            if obecny.kategoria_id == kategoria_id:
                nowy.id = obecny.id
                self._budzety.zmien(nowy)
                return nowy
        return self._budzety.dodaj(nowy)

    def usun(self, budzet: Budzet) -> None:
        """Usuwa budżet."""
        self._budzety.usun(budzet.id)

    def skopiuj_poprzedni(self, miesiac: date) -> int:
        """Kopiuje z poprzedniego miesiąca budżety, których jeszcze nie ma."""
        zajete = {b.kategoria_id for b in self.z_miesiaca(miesiac)}
        poprzednie = self.z_miesiaca(przesun_miesiac(miesiac.replace(day=1), -1))
        nowe = [b for b in poprzednie if b.kategoria_id not in zajete]
        for budzet in nowe:
            self._budzety.dodaj(replace(budzet, miesiac=miesiac.replace(day=1), id=None))
        return len(nowe)

    def wykonanie(self, miesiac: date) -> list[WykonanieBudzetu]:
        """Zwraca wykonanie budżetów miesiąca, od najbardziej wykorzystanego."""
        prog = self._ustawienia.wczytaj().prog_ostrzezen
        nazwy = self._kategorie.nazwy()
        transakcje = z_miesiaca(self._transakcje.wszystkie(), miesiac)
        wynik = []
        for budzet in self.z_miesiaca(miesiac):
            wydano = suma_wydatkow(
                [t for t in transakcje if t.kategoria_id == budzet.kategoria_id]
            )
            wynik.append(
                WykonanieBudzetu(
                    budzet,
                    nazwy[budzet.kategoria_id],
                    wydano,
                    budzet.procent(wydano),
                    budzet.stan(wydano, prog),
                )
            )
        return sorted(wynik, key=lambda w: w.procent, reverse=True)

    def ostrzezenia(self, miesiac: date) -> list[WykonanieBudzetu]:
        """Zwraca budżety przekroczone lub bliskie limitu."""
        return [w for w in self.wykonanie(miesiac) if w.stan is not StanBudzetu.W_NORMIE]


class SerwisCeli:
    """Cele oszczędnościowe i wpłaty na nie."""

    def __init__(self, cele: RepozytoriumCeli, wplaty: RepozytoriumWplat) -> None:
        self._cele = cele
        self._wplaty = wplaty

    def wszystkie(self) -> list[Cel]:
        """Zwraca cele z policzoną sumą wpłat, od najbliższego terminu."""
        wplaty = self._wplaty.wszystkie()
        cele = [
            replace(cel, odlozono=sum((w.kwota for w in wplaty if w.cel_id == cel.id), ZERO))
            for cel in self._cele.wszystkie()
        ]
        return sorted(cele, key=lambda cel: cel.termin)

    def sprawdz_nazwe(self, nazwa: str) -> None:
        """Zgłasza błąd, gdy nazwa jest już zajęta."""
        sprawdz_unikalnosc(nazwa, {cel.nazwa for cel in self._cele.wszystkie()})

    def dodaj(self, nazwa: str, kwota: Decimal, termin: date) -> Cel:
        """Dodaje cel o niepowtarzalnej nazwie."""
        self.sprawdz_nazwe(nazwa)
        return self._cele.dodaj(Cel(nazwa, kwota, termin))

    def wplac(self, cel: Cel, kwota: Decimal, data: date | None = None) -> WplataCelu:
        """Zapisuje wpłatę na cel, domyślnie z dzisiejszą datą."""
        return self._wplaty.dodaj(WplataCelu(cel.id, data or date.today(), kwota))

    def usun(self, cel: Cel) -> None:
        """Usuwa cel razem z wpłatami."""
        self._cele.usun(cel.id)
