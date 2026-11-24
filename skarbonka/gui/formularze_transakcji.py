"""Formularze dodawania i edycji transakcji."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from skarbonka.gui.formularz import Formularz, Pole
from skarbonka.models.kurs import Kurs
from skarbonka.models.transakcja import Przelew, Transakcja, Wydatek
from skarbonka.services.waluty import WALUTY
from skarbonka.utils.formatowanie import formatuj_date
from skarbonka.utils.walidacja import parsuj_date, parsuj_kurs, parsuj_kwote, sprawdz_tekst
from skarbonka.wyjatki import BladWalidacji

if TYPE_CHECKING:
    from skarbonka.gui.okno import Okno


def data_nie_z_przyszlosci(tekst: str) -> date:
    """Zamienia tekst na datę nie późniejszą niż dzisiejsza."""
    return parsuj_date(tekst, najpozniej=date.today())


def opis_pola(tekst: str) -> str:
    """Sprawdza opis transakcji."""
    return sprawdz_tekst(tekst, "Opis")


def _kurs_opcjonalny(tekst: str) -> Decimal | None:
    """Zwraca wpisany kurs albo None, gdy pole jest puste."""
    return parsuj_kurs(tekst) if tekst.strip() else None


def _pole_daty(wartosc: date | None = None) -> Pole:
    return Pole("data", "Data", data_nie_z_przyszlosci, formatuj_date(wartosc or date.today()))


def _pola_opisu(okno: "Okno", rodzaj: type[Transakcja], stara: Transakcja | None = None) -> list:
    """Zwraca pola opisu i kategorii. Reguły podpowiadają kategorię po wpisaniu opisu."""
    serwisy = okno.serwisy
    kategorie = {k.nazwa: k for k in serwisy.kategorie.pasujace(rodzaj)}

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
        Pole("kategoria", "Kategoria", wartosc=obecna, wybor=kategorie),
    ]


def _zapisz(okno: "Okno", transakcja: Transakcja) -> None:
    """Dodaje transakcję, a przy przekroczonym budżecie pokazuje ostrzeżenie."""
    okno.serwisy.transakcje.dodaj(transakcja)
    okno.powiadom(f"Dodano: {transakcja.opis}")
    for w in okno.serwisy.budzety.ostrzezenia(transakcja.data):
        if w.budzet.kategoria_id == transakcja.kategoria_id:
            okno.powiadom(f"Dodano. Budżet {w.kategoria}: {w.stan}.", "uwaga")


def nowa_transakcja(okno: "Okno", rodzaj: type[Transakcja]) -> Formularz:
    """Otwiera formularz wydatku albo przychodu."""
    konta = {k.nazwa: k for k in okno.serwisy.konta.wszystkie()}

    def zapisz(dane: dict[str, Any]) -> None:
        _zapisz(
            okno,
            rodzaj(
                dane["data"], dane["kwota"], dane["opis"], dane["konto"].id, dane["kategoria"].id
            ),
        )

    pola = [
        Pole("kwota", "Kwota w zł", parsuj_kwote),
        _pole_daty(),
        Pole("konto", "Konto", wybor=konta),
        *_pola_opisu(okno, rodzaj),
    ]
    return Formularz(okno, f"Nowy {rodzaj.RODZAJ}", pola, zapisz, "Dodaj")


def nowy_przelew(okno: "Okno") -> Formularz:
    """Otwiera formularz przelewu między kontami."""
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
        Pole("kwota", "Kwota w zł", parsuj_kwote),
        _pole_daty(),
        Pole("zrodlo", "Z konta", wybor=konta),
        Pole("cel", "Na konto", wartosc=list(konta)[1], wybor=konta),
    ]
    return Formularz(okno, "Nowy przelew", pola, zapisz, "Dodaj")


def wydatek_w_walucie(okno: "Okno") -> Formularz:
    """Otwiera formularz wydatku przeliczanego po kursie NBP."""
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

    pola = [
        Pole("waluta", "Waluta", wybor={waluta: waluta for waluta in WALUTY}),
        Pole("kwota", "Kwota w walucie", parsuj_kwote),
        _pole_daty(),
        Pole("kurs", "Kurs (puste = pobierz z NBP)", _kurs_opcjonalny),
        Pole("konto", "Konto", wybor=konta),
        *_pola_opisu(okno, Wydatek),
    ]
    return Formularz(okno, "Wydatek w obcej walucie", pola, zapisz, "Dodaj")


def edycja(okno: "Okno", stara: Transakcja) -> Formularz:
    """Otwiera formularz zmiany istniejącej transakcji."""
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

    pola = [
        Pole("kwota", "Kwota w zł", parsuj_kwote, f"{stara.kwota:.2f}".replace(".", ",")),
        _pole_daty(stara.data),
    ]
    if czy_przelew:
        pola.append(Pole("opis", "Opis", opis_pola, stara.opis))
    else:
        konta = {k.nazwa: k for k in serwisy.konta.wszystkie()}
        nazwa_konta = serwisy.konta.nazwy()[stara.konto_id]
        pola.append(Pole("konto", "Konto", wartosc=nazwa_konta, wybor=konta))
        pola += _pola_opisu(okno, type(stara), stara)
    return Formularz(okno, f"Edycja: {stara.RODZAJ}", pola, zapisz)
