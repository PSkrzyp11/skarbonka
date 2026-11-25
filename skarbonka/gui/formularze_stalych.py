"""Panele dodawania i edycji stałych przychodów i opłat."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from skarbonka.config import MAKS_DLUGOSC_NAZWY
from skarbonka.gui.formularz import Formularz, Pole
from skarbonka.models.cykliczna import KLASY_CYKLICZNE, MAKS_ODSTEP, Cykliczna
from skarbonka.models.enums import Czestotliwosc
from skarbonka.models.transakcja import Przychod, Transakcja, Wydatek
from skarbonka.services.cykliczne import NAJSTARSZY_START, RODZAJE_KWOTY, Platnosc
from skarbonka.services.osoby import WSPOLNE
from skarbonka.utils.formatowanie import formatuj_date, formatuj_miesiac
from skarbonka.utils.walidacja import parsuj_date, parsuj_kwote, parsuj_liczbe, sprawdz_tekst

if TYPE_CHECKING:
    from skarbonka.gui.okno import Okno

TYTULY = {Przychod: "Stały przychód", Wydatek: "Stała opłata"}
PRZYKLADY = {Przychod: "pensja", Wydatek: "czynsz"}


def _parser_terminu(stara: Cykliczna | None) -> Any:
    """Zwraca funkcję sprawdzającą termin. Niezmieniony termin jest zawsze poprawny."""

    def parser(tekst: str) -> date:
        if stara is not None and tekst == formatuj_date(stara.nastepny):
            return stara.nastepny
        return parsuj_date(tekst, najwczesniej=date.today() - NAJSTARSZY_START)

    return parser


def _odstep(tekst: str) -> tuple[Czestotliwosc, int]:
    """Zamienia tekst, np. 2 miesiące, na jednostkę i liczbę."""
    liczba, _, jednostka = tekst.rpartition(" ")
    return Czestotliwosc.z_odmiany(jednostka), parsuj_liczbe(liczba, MAKS_ODSTEP, minimum=1)


def _nazwa(tekst: str) -> str:
    """Sprawdza nazwę. To, czy jest wolna, zależy jeszcze od osoby."""
    return sprawdz_tekst(tekst, "Nazwa", MAKS_DLUGOSC_NAZWY)


def _rodzaj_kwoty(zmienna: bool) -> str:
    """Zwraca nazwę rodzaju kwoty."""
    return next(nazwa for nazwa, czy in RODZAJE_KWOTY.items() if czy == zmienna)


def _tekst_kwoty(kwota: Decimal) -> str:
    """Zapisuje kwotę tak, jak wpisuje ją użytkownik."""
    return f"{kwota:.2f}".replace(".", ",")


def _pola_osoby(okno: "Okno", osoba_id: int | None) -> list[Pole]:
    """Zwraca pole wyboru osoby albo nic, gdy nie ma osób."""
    wybor = okno.serwisy.osoby.wybor()
    if len(wybor) == 1:
        return []
    obecna = okno.serwisy.osoby.nazwy().get(osoba_id, WSPOLNE)
    return [Pole("osoba", "Czyje", wartosc=obecna, wybor=wybor)]


def _pola(
    okno: "Okno", rodzaj: type[Transakcja], osoba_id: int | None, stara: Cykliczna | None = None
) -> list[Pole]:
    """Zwraca pola panelu. Przy edycji są wypełnione."""
    serwisy = okno.serwisy
    return [
        Pole(
            "kwota",
            "Kwota",
            parsuj_kwote,
            _tekst_kwoty(stara.kwota) if stara else "",
            rodzaj="kwota",
        ),
        Pole(
            "zmienna",
            "Rodzaj kwoty",
            wartosc=_rodzaj_kwoty(stara is not None and stara.zmienna),
            wybor=RODZAJE_KWOTY,
        ),
        Pole(
            "nazwa",
            f"Nazwa, np. {PRZYKLADY[rodzaj]}",
            _nazwa,
            stara.nazwa if stara else "",
        ),
        *_pola_osoby(okno, osoba_id),
        Pole(
            "odstep",
            "Powtarzanie co",
            _odstep,
            stara.czestotliwosc.okres(stara.co) if stara else Czestotliwosc.MIESIAC.okres(1),
            rodzaj="odstep",
        ),
        Pole(
            "termin",
            "Następny termin" if stara else "Pierwszy termin",
            _parser_terminu(stara),
            formatuj_date(stara.nastepny if stara else date.today()),
            rodzaj="data",
        ),
        Pole(
            "kategoria",
            "Kategoria",
            wartosc=serwisy.kategorie.nazwy()[stara.kategoria_id] if stara else "",
            wybor={k.nazwa: k for k in serwisy.kategorie.pasujace(rodzaj)},
            rodzaj="kafelki",
        ),
        Pole(
            "konto",
            "Konto",
            wartosc=serwisy.konta.nazwy()[stara.konto_id] if stara else "",
            wybor={k.nazwa: k for k in serwisy.konta.wszystkie()},
        ),
    ]


def nowa_stala(
    okno: "Okno", rodzaj: type[Transakcja], osoba_id: int | None = None
) -> Formularz:
    """Otwiera panel nowego stałego przychodu albo opłaty."""

    def zapisz(dane: dict[str, Any]) -> None:
        czestotliwosc, co = dane["odstep"]
        okno.serwisy.cykliczne.dodaj(
            Cykliczna(
                dane["nazwa"],
                rodzaj.RODZAJ,
                dane["kwota"],
                dane["konto"].id,
                dane["kategoria"].id,
                dane["termin"],
                czestotliwosc,
                osoba_id=dane.get("osoba"),
                zmienna=dane["zmienna"],
                co=co,
            )
        )
        okno.powiadom(f"Dodano: {dane['nazwa']}")

    return Formularz(okno, TYTULY[rodzaj], _pola(okno, rodzaj, osoba_id), zapisz, "Dodaj")


def edycja_stalej(okno: "Okno", stara: Cykliczna) -> Formularz:
    """Otwiera panel zmiany. Zaksięgowane transakcje się nie zmieniają."""
    rodzaj = KLASY_CYKLICZNE[stara.rodzaj]

    def zapisz(dane: dict[str, Any]) -> None:
        zmieniona = replace(
            stara,
            nazwa=dane["nazwa"],
            kwota=dane["kwota"],
            konto_id=dane["konto"].id,
            kategoria_id=dane["kategoria"].id,
            osoba_id=dane.get("osoba"),
            zmienna=dane["zmienna"],
        )
        okno.serwisy.cykliczne.zmien(zmieniona.przeplanuj(dane["termin"], *dane["odstep"]))
        okno.powiadom("Zapisano zmiany.")

    pola = _pola(okno, rodzaj, stara.osoba_id, stara)
    return Formularz(okno, TYTULY[rodzaj], pola, zapisz)


def kwota_terminu(okno: "Okno", platnosc: Platnosc) -> Formularz:
    """Otwiera panel z kwotą jednego terminu. Zaksięgowaną kwotę poprawia."""
    stala, serwis = platnosc.cykliczna, okno.serwisy.cykliczne

    def zapisz(dane: dict[str, Any]) -> None:
        if platnosc.transakcja is None:
            serwis.zaksieguj(stala, platnosc.termin, kwota=dane["kwota"])
        else:
            serwis.popraw(stala, platnosc.transakcja, dane["kwota"])
        okno.powiadom(f"Zapisano: {serwis.opis(stala)}")

    pole = Pole(
        "kwota",
        f"Kwota za {formatuj_miesiac(platnosc.termin)}",
        parsuj_kwote,
        _tekst_kwoty(abs(platnosc.wplyw)),
        rodzaj="kwota",
    )
    return Formularz(okno, serwis.opis(stala), [pole], zapisz)
