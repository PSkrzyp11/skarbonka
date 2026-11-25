"""Panele dodawania i edycji transakcji."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from skarbonka.gui.formularz import Formularz, Pole, Przelacznik
from skarbonka.gui.pole_kategorii import pole_kategorii
from skarbonka.models.kurs import Kurs
from skarbonka.models.transakcja import Przelew, Przychod, Transakcja, Wydatek
from skarbonka.services.waluty import WALUTY
from skarbonka.utils.formatowanie import formatuj_date
from skarbonka.utils.walidacja import parsuj_date, parsuj_kurs, parsuj_kwote, sprawdz_tekst
from skarbonka.wyjatki import BladWalidacji

if TYPE_CHECKING:
    from skarbonka.gui.okno import Okno

TYTUL = "Nowa transakcja"
WYDATEK, PRZYCHOD, PRZELEW, WALUTA = "Wydatek", "Przychód", "Przelew", "Waluta"


def data_nie_z_przyszlosci(tekst: str) -> date:
    """Zamienia tekst na datę nie późniejszą niż dzisiejsza."""
    return parsuj_date(tekst, najpozniej=date.today())


def opis_pola(tekst: str) -> str:
    """Sprawdza opis transakcji."""
    return sprawdz_tekst(tekst, "Opis")


def _kurs_opcjonalny(tekst: str) -> Decimal | None:
    """Zwraca wpisany kurs albo None, gdy pole jest puste."""
    return parsuj_kurs(tekst) if tekst.strip() else None


def _pole_kwoty(etykieta: str = "Kwota", wartosc: str = "") -> Pole:
    return Pole("kwota", etykieta, parsuj_kwote, wartosc, rodzaj="kwota")


def _pole_daty(wartosc: date | None = None) -> Pole:
    tekst = formatuj_date(wartosc or date.today())
    return Pole("data", "Data", data_nie_z_przyszlosci, tekst, rodzaj="data")


def _przelacznik(okno: "Okno", wybrana: str) -> Przelacznik:
    """Zwraca przełącznik rodzaju transakcji na górze panelu."""
    return Przelacznik(
        {
            WYDATEK: lambda: nowa_transakcja(okno, Wydatek),
            PRZYCHOD: lambda: nowa_transakcja(okno, Przychod),
            PRZELEW: lambda: nowy_przelew(okno),
            WALUTA: lambda: wydatek_w_walucie(okno),
        },
        wybrana,
    )


def _pola_opisu(
    okno: "Okno", rodzaj: type[Transakcja], stara: Transakcja | None = None
) -> list[Pole]:
    """Zwraca pola opisu i kategorii. Reguły podpowiadają kategorię w trakcie pisania."""
    serwisy = okno.serwisy

    def podpowiedz(formularz: Formularz) -> None:
        kategoria = serwisy.kategoryzator.dopasuj(formularz.wartosc("opis"), rodzaj)
        if kategoria is not None:
            formularz.ustaw("kategoria", kategoria.nazwa)

    obecna = serwisy.kategorie.nazwy().get(stara.kategoria_id, "") if stara else ""
    return [
        Pole(
            "opis",
            "Opis",
            opis_pola,
            stara.opis if stara else "",
            po_zmianie=None if stara else podpowiedz,
        ),
        pole_kategorii(okno, rodzaj, obecna),
    ]


def _zapisz(okno: "Okno", transakcja: Transakcja) -> None:
    """Dodaje transakcję, a przy przekroczonym budżecie pokazuje ostrzeżenie."""
    okno.serwisy.transakcje.dodaj(transakcja)
    okno.powiadom(f"Dodano: {transakcja.opis}")
    for w in okno.serwisy.budzety.ostrzezenia(transakcja.data):
        if w.budzet.kategoria_id == transakcja.kategoria_id:
            okno.powiadom(f"Dodano. Budżet {w.kategoria}: {w.stan}.", "uwaga")


def nowa_transakcja(okno: "Okno", rodzaj: type[Transakcja]) -> Formularz:
    """Otwiera panel wydatku albo przychodu."""
    konta = {k.nazwa: k for k in okno.serwisy.konta.wszystkie()}

    def zapisz(dane: dict[str, Any]) -> None:
        _zapisz(
            okno,
            rodzaj(
                dane["data"], dane["kwota"], dane["opis"], dane["konto"].id, dane["kategoria"].id
            ),
        )

    pola = [
        _pole_kwoty(),
        *_pola_opisu(okno, rodzaj),
        _pole_daty(),
        Pole("konto", "Konto", wybor=konta),
    ]
    wybrana = WYDATEK if rodzaj is Wydatek else PRZYCHOD
    przelacznik = _przelacznik(okno, wybrana)
    return Formularz(okno, TYTUL, pola, zapisz, f"Dodaj {rodzaj.RODZAJ}", przelacznik)


def nowy_przelew(okno: "Okno") -> Formularz:
    """Otwiera panel przelewu między kontami."""
    konta = {k.nazwa: k for k in okno.serwisy.konta.wszystkie()}
    if len(konta) < 2:
        raise BladWalidacji("Przelew wymaga co najmniej dwóch kont.")

    def zapisz(dane: dict[str, Any]) -> None:
        zrodlo, cel = dane["zrodlo"], dane["cel"]
        opis = f"{zrodlo.nazwa} -> {cel.nazwa}"
        _zapisz(
            okno,
            Przelew(dane["data"], dane["kwota"], opis, zrodlo.id, konto_docelowe_id=cel.id),
        )

    pola = [
        _pole_kwoty(),
        Pole("zrodlo", "Z konta", wybor=konta),
        Pole("cel", "Na konto", wartosc=list(konta)[1], wybor=konta),
        _pole_daty(),
    ]
    return Formularz(okno, TYTUL, pola, zapisz, "Dodaj przelew", _przelacznik(okno, PRZELEW))


def wydatek_w_walucie(okno: "Okno") -> Formularz:
    """Otwiera panel wydatku przeliczanego po kursie NBP."""
    konta = {k.nazwa: k for k in okno.serwisy.konta.wszystkie()}

    def zapisz(dane: dict[str, Any]) -> None:
        waluta = dane["waluta"]
        if dane["kurs"] is None:
            kurs = okno.serwisy.waluty.kurs(waluta, dane["data"])
        else:
            kurs = Kurs(waluta, dane["data"], dane["kurs"])
        _zapisz(
            okno,
            Wydatek(
                dane["data"],
                kurs.przelicz(dane["kwota"]),
                dane["opis"],
                dane["konto"].id,
                dane["kategoria"].id,
                waluta=waluta,
                kwota_oryg=dane["kwota"],
            ),
        )

    def pokaz_walute(formularz: Formularz) -> None:
        formularz.ustaw_jednostke("kwota", formularz.wartosc("waluta"))

    pola = [
        _pole_kwoty("Kwota w walucie"),
        Pole(
            "waluta",
            "Waluta",
            wybor={waluta: waluta for waluta in WALUTY},
            po_zmianie=pokaz_walute,
        ),
        Pole("kurs", "Kurs (puste pobiera z NBP)", _kurs_opcjonalny),
        *_pola_opisu(okno, Wydatek),
        _pole_daty(),
        Pole("konto", "Konto", wybor=konta),
    ]
    formularz = Formularz(okno, TYTUL, pola, zapisz, "Dodaj wydatek", _przelacznik(okno, WALUTA))
    pokaz_walute(formularz)
    return formularz


def edycja(okno: "Okno", stara: Transakcja) -> Formularz:
    """Otwiera panel zmiany istniejącej transakcji."""
    serwisy = okno.serwisy
    czy_przelew = isinstance(stara, Przelew)

    def zapisz(dane: dict[str, Any]) -> None:
        zmiany = {"kwota": dane["kwota"], "data": dane["data"], "opis": dane["opis"]}
        if not czy_przelew:
            zmiany |= {"konto_id": dane["konto"].id, "kategoria_id": dane["kategoria"].id}
        if dane["kwota"] != stara.kwota:
            zmiany |= {"waluta": "PLN", "kwota_oryg": None}
        serwisy.transakcje.zmien(replace(stara, **zmiany))
        okno.powiadom("Zapisano zmiany.")

    pola = [_pole_kwoty(wartosc=f"{stara.kwota:.2f}".replace(".", ","))]
    if czy_przelew:
        pola += [Pole("opis", "Opis", opis_pola, stara.opis), _pole_daty(stara.data)]
    else:
        konta = {k.nazwa: k for k in serwisy.konta.wszystkie()}
        nazwa_konta = serwisy.konta.nazwy()[stara.konto_id]
        pola += [
            *_pola_opisu(okno, type(stara), stara),
            _pole_daty(stara.data),
            Pole("konto", "Konto", wartosc=nazwa_konta, wybor=konta),
        ]
    return Formularz(okno, f"Edycja: {stara.RODZAJ}", pola, zapisz)
