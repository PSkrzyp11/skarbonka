"""Transakcje powtarzające się, np. czynsz albo abonament."""

from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from skarbonka.models.enums import Czestotliwosc
from skarbonka.models.transakcja import Przychod, Transakcja, Wydatek
from skarbonka.utils.daty import przesun_miesiac
from skarbonka.wyjatki import BladWalidacji, NieprawidlowaData, NieprawidlowaKwota

GROSZ = Decimal("0.01")
MIESIECY_W_ROKU = 12
MIESIECY_W_KWARTALE = 3
RAZY_W_ROKU = {
    Czestotliwosc.TYDZIEN: 52,
    Czestotliwosc.MIESIAC: MIESIECY_W_ROKU,
    Czestotliwosc.KWARTAL: 4,
    Czestotliwosc.ROK: 1,
}
KLASY_CYKLICZNE = {klasa.RODZAJ: klasa for klasa in (Wydatek, Przychod)}


@dataclass
class Cykliczna:
    """Wzór, według którego powstają kolejne transakcje.

    Pozycja zmienna, np. pensja godzinowa, pamięta ostatnio wpisaną kwotę.
    """

    nazwa: str
    rodzaj: str
    kwota: Decimal
    konto_id: int
    kategoria_id: int
    start: date
    czestotliwosc: Czestotliwosc
    ostatnia: date | None = None
    aktywna: bool = True
    osoba_id: int | None = None
    zmienna: bool = False
    id: int | None = None

    def __post_init__(self) -> None:
        if self.kwota <= 0:
            raise NieprawidlowaKwota("Kwota transakcji musi być dodatnia.")
        if self.rodzaj not in KLASY_CYKLICZNE:
            raise BladWalidacji(f"Nieznany rodzaj transakcji: {self.rodzaj}.")

    def termin(self, numer: int) -> date:
        """Zwraca termin o podanym numerze, licząc od zera.

        Każdy termin liczy się od daty startu, dzięki czemu płatność z 31. dnia
        po krótkim lutym wraca w marcu na 31.
        """
        match self.czestotliwosc:
            case Czestotliwosc.TYDZIEN:
                return self.start + timedelta(weeks=numer)
            case Czestotliwosc.MIESIAC:
                return przesun_miesiac(self.start, numer)
            case Czestotliwosc.KWARTAL:
                return przesun_miesiac(self.start, numer * MIESIECY_W_KWARTALE)
            case Czestotliwosc.ROK:
                return przesun_miesiac(self.start, numer * MIESIECY_W_ROKU)

    def terminy(self, od: date, do: date) -> Iterator[date]:
        """Generator: oddaje kolejne terminy z podanego zakresu dat."""
        numer = 0
        while True:
            termin = self.termin(numer)
            numer += 1
            if termin > do:
                break
            if termin < od:
                continue
            yield termin

    def niezaksiegowane(self, do: date) -> Iterator[date]:
        """Generator: oddaje terminy po ostatnim zaksięgowanym."""
        od = self.start if self.ostatnia is None else self.ostatnia + timedelta(days=1)
        yield from self.terminy(od, do)

    def poprzedni(self, termin: date) -> date:
        """Zwraca termin tuż przed podanym albo najwcześniejszą możliwą datę."""
        return max((t for t in self.terminy(self.start, termin) if t < termin), default=date.min)

    @property
    def nastepny(self) -> date:
        """Najbliższy termin, który nie jest jeszcze zaksięgowany."""
        return next(self.niezaksiegowane(date.max))

    def przeplanuj(self, nastepny: date, czestotliwosc: Czestotliwosc) -> "Cykliczna":
        """Zwraca kopię z nowym najbliższym terminem i częstotliwością.

        Bez zmian zostaje stara data startu, żeby nie zgubić np. 31. dnia miesiąca.
        """
        if (nastepny, czestotliwosc) == (self.nastepny, self.czestotliwosc):
            return replace(self)
        if self.ostatnia is not None and nastepny <= self.ostatnia:
            raise NieprawidlowaData("Następny termin musi być po ostatnim zaksięgowanym.")
        return replace(self, start=nastepny, czestotliwosc=czestotliwosc)

    def utworz_transakcje(self, termin: date) -> Transakcja:
        """Tworzy transakcję na podany dzień."""
        klasa = KLASY_CYKLICZNE[self.rodzaj]
        return klasa(
            termin,
            self.kwota,
            self.nazwa,
            self.konto_id,
            self.kategoria_id,
            cykliczna_id=self.id,
        )

    @property
    def wplyw(self) -> Decimal:
        """Zmiana łącznego stanu pieniędzy po jednym zaksięgowaniu."""
        return self.kwota if self.rodzaj == Przychod.RODZAJ else -self.kwota

    @property
    def miesiecznie(self) -> Decimal:
        """Wpływ w przeliczeniu na jeden miesiąc, np. roczna opłata podzielona przez 12."""
        rocznie = self.wplyw * RAZY_W_ROKU[self.czestotliwosc]
        return (rocznie / MIESIECY_W_ROKU).quantize(GROSZ, rounding=ROUND_HALF_UP)

    def __str__(self) -> str:
        return self.nazwa
