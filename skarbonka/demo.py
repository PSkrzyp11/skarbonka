"""Przykładowe dane do pokazania aplikacji bez prawdziwych finansów.

Losowość ma stałe ziarno, więc te same daty dają zawsze te same transakcje.
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from skarbonka.models.cykliczna import Cykliczna
from skarbonka.models.enums import Czestotliwosc, TypKonta
from skarbonka.models.transakcja import Przelew, Wydatek
from skarbonka.services.analizy import wydatki_wg_kategorii, z_miesiaca
from skarbonka.services.zestaw import Serwisy
from skarbonka.storage.baza import Baza
from skarbonka.utils.daty import przesun_miesiac

ZIARNO = 42
MIESIACE_HISTORII = 5

ZAKUPY = (
    ("Biedronka", "Jedzenie", 35, 190, 0.45),
    ("Piekarnia", "Jedzenie", 6, 28, 0.35),
    ("Obiad na mieście", "Jedzenie", 28, 75, 0.15),
    ("Paliwo", "Transport", 120, 260, 0.06),
    ("Bilet MPK", "Transport", 4, 20, 0.15),
    ("Apteka", "Zdrowie", 15, 90, 0.05),
    ("Kino", "Rozrywka", 25, 70, 0.06),
    ("Sklep odzieżowy", "Ubrania", 60, 280, 0.03),
    ("Kwiaciarnia", "Inne wydatki", 20, 80, 0.03),
)
REGULY = {
    "biedronka": "Jedzenie",
    "piekarnia": "Jedzenie",
    "paliwo": "Transport",
    "kino": "Rozrywka",
}
WSPOLCZYNNIKI_BUDZETOW = {"Jedzenie": "0.9", "Transport": "1.15", "Rozrywka": "2"}
NAJMNIEJSZY_BUDZET = Decimal("50")


def wypelnij(baza: Baza, serwisy: Serwisy, dzis: date | None = None) -> None:
    """Dodaje przykładowe konta, transakcje i plany. Całość albo nic."""
    dzis = dzis or date.today()
    start = przesun_miesiac(dzis.replace(day=1), -MIESIACE_HISTORII)
    with baza.transakcja():
        kategorie = {k.nazwa: k.id for k in serwisy.kategorie.wszystkie()}
        portfel = serwisy.konta.wszystkie()[0]
        ror = serwisy.konta.dodaj("ROR", TypKonta.BIEZACE, Decimal("2500"))
        oszczednosci = serwisy.konta.dodaj("Oszczędności", TypKonta.OSZCZEDNOSCI, Decimal("4000"))

        _dodaj_zakupy(serwisy, kategorie, portfel.id, ror.id, start, dzis)
        _dodaj_przelewy(serwisy, ror.id, portfel.id, oszczednosci.id, start, dzis)
        _dodaj_cykliczne(serwisy, kategorie, ror.id, start, dzis)
        _dodaj_przyszle(serwisy, kategorie, ror.id, dzis)
        _dodaj_plany(serwisy, dzis)


def _dodaj_zakupy(
    serwisy: Serwisy, kategorie: dict[str, int], portfel: int, ror: int, start: date, dzis: date
) -> None:
    """Dodaje codzienne zakupy oraz jeden wydatek w euro."""
    losowe = random.Random(ZIARNO)
    for i in range((dzis - start).days + 1):
        for opis, kategoria, minimum, maksimum, szansa in ZAKUPY:
            if losowe.random() > szansa:
                continue
            kwota = Decimal(losowe.randint(minimum * 100, maksimum * 100)).scaleb(-2)
            konto = losowe.choice((portfel, ror, ror))
            data = start + timedelta(days=i)
            serwisy.transakcje.dodaj(Wydatek(data, kwota, opis, konto, kategorie[kategoria]))
    serwisy.transakcje.dodaj(
        Wydatek(
            przesun_miesiac(dzis, -1),
            Decimal("106.94"),
            "Muzeum w Berlinie",
            ror,
            kategorie["Rozrywka"],
            waluta="EUR",
            kwota_oryg=Decimal("24.00"),
        )
    )


def _dodaj_przelewy(
    serwisy: Serwisy, ror: int, portfel: int, oszczednosci: int, start: date, dzis: date
) -> None:
    """Co miesiąc zasila portfel i konto oszczędnościowe."""
    for i in range(MIESIACE_HISTORII + 1):
        for dzien, cel, kwota, opis in (
            (2, portfel, "900", "Wypłata z bankomatu"),
            (3, oszczednosci, "400", "Oszczędności"),
        ):
            data = przesun_miesiac(start, i).replace(day=dzien)
            if data <= dzis:
                serwisy.transakcje.dodaj(
                    Przelew(data, Decimal(kwota), opis, ror, konto_docelowe_id=cel)
                )


def _dodaj_cykliczne(
    serwisy: Serwisy, kategorie: dict[str, int], ror: int, start: date, dzis: date
) -> None:
    """Dodaje stałe pozycje. Ostatni termin internetu zostaje zaległy."""
    kuba = serwisy.osoby.dodaj("Kuba").id
    wzory = (
        ("Pensja", "przychód", "6200", "Wynagrodzenie", 1, kuba),
        ("Czynsz", "wydatek", "1850", "Mieszkanie", 10, None),
        ("Internet", "wydatek", "59.99", "Mieszkanie", 5, None),
    )
    for nazwa, rodzaj, kwota, kategoria, dzien, osoba in wzory:
        cykliczna = serwisy.cykliczne.dodaj(
            Cykliczna(
                nazwa,
                rodzaj,
                Decimal(kwota),
                ror,
                kategorie[kategoria],
                start.replace(day=dzien),
                Czestotliwosc.MIESIAC,
                osoba_id=osoba,
            ),
            dzis,
        )
        terminy = list(cykliczna.niezaksiegowane(dzis))
        if nazwa == "Internet":
            terminy.pop()
        for termin in terminy:
            serwisy.cykliczne.zaksieguj(cykliczna, termin)


def _dodaj_przyszle(
    serwisy: Serwisy, kategorie: dict[str, int], ror: int, dzis: date
) -> None:
    """Dodaje drugą osobę i pozycje, których pierwszy termin dopiero nadejdzie."""
    kuba, ola = serwisy.osoby.wszystkie()[0].id, serwisy.osoby.dodaj("Ola").id
    wzory = (
        ("Zlecenia", "przychód", "4300", "Wynagrodzenie", Czestotliwosc.MIESIAC, ola),
        ("Siłownia", "wydatek", "129", "Zdrowie", Czestotliwosc.MIESIAC, ola),
        ("Ubezpieczenie auta", "wydatek", "1260", "Transport", Czestotliwosc.ROK, kuba),
        ("Prąd", "wydatek", "390", "Mieszkanie", Czestotliwosc.KWARTAL, None),
    )
    for nazwa, rodzaj, kwota, kategoria, czestotliwosc, osoba in wzory:
        serwisy.cykliczne.dodaj(
            Cykliczna(
                nazwa,
                rodzaj,
                Decimal(kwota),
                ror,
                kategorie[kategoria],
                przesun_miesiac(dzis, 1),
                czestotliwosc,
                osoba_id=osoba,
                zmienna=nazwa in ("Zlecenia", "Prąd"),
            ),
            dzis,
        )


def _dodaj_plany(serwisy: Serwisy, dzis: date) -> None:
    """Dodaje reguły, cele i budżety dopasowane do wydatków tego miesiąca."""
    kategorie = {k.nazwa: k for k in serwisy.kategorie.wszystkie()}
    for fraza, nazwa in REGULY.items():
        serwisy.kategoryzator.dodaj(fraza, kategorie[nazwa])

    wakacje = serwisy.cele.dodaj("Wakacje", Decimal("5000"), przesun_miesiac(dzis, 7))
    rower = serwisy.cele.dodaj("Rower", Decimal("1800"), przesun_miesiac(dzis, 2))
    for cel, kwota in ((wakacje, "1350"), (rower, "1500")):
        serwisy.cele.wplac(cel, Decimal(kwota), dzis)

    transakcje = z_miesiaca(serwisy.transakcje.wszystkie(), dzis)
    wydatki = wydatki_wg_kategorii(transakcje, list(kategorie.values()))
    for nazwa, wspolczynnik in WSPOLCZYNNIKI_BUDZETOW.items():
        limit = wydatki.get(nazwa, NAJMNIEJSZY_BUDZET) * Decimal(wspolczynnik)
        serwisy.budzety.ustaw(
            kategorie[nazwa].id, dzis, max(limit.quantize(Decimal(1)), NAJMNIEJSZY_BUDZET)
        )
