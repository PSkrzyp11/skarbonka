"""Wypisywanie danych na ekran: kolory, tabele i ramki z biblioteki rich.

Teksty od użytkownika trafiają do obiektów Text, żeby nawiasy kwadratowe
w opisie nie zostały potraktowane jako polecenia formatowania.
"""

from collections.abc import Callable
from datetime import date
from decimal import Decimal

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from skarbonka.config import NAZWA_APLIKACJI, SLOWO_ANULUJ
from skarbonka.models.cykliczna import Cykliczna
from skarbonka.models.enums import StanBudzetu, StanPlatnosci
from skarbonka.models.konto import Konto
from skarbonka.models.plan import Cel
from skarbonka.models.transakcja import Transakcja
from skarbonka.services.bilans_stalych import (
    BilansStalych,
    GrupaStalych,
    Platnosc,
    policz_bilans,
)
from skarbonka.services.planowanie import WykonanieBudzetu
from skarbonka.utils.formatowanie import (
    formatuj_date,
    formatuj_kwote,
    formatuj_miesiac,
    formatuj_procent,
)

KOLORY_RODZAJOW = {"wydatek": "red", "przychód": "green", "przelew": "cyan"}

KOLORY_BUDZETU = {
    StanBudzetu.W_NORMIE: "green",
    StanBudzetu.UWAGA: "yellow",
    StanBudzetu.PRZEKROCZONY: "red",
}

KOLORY_PLATNOSCI = {
    StanPlatnosci.ZALATWIONA: "green",
    StanPlatnosci.CZEKA: "yellow",
    StanPlatnosci.NADCHODZI: "",
}

konsola = Console(highlight=False)


def wylacz_kolory() -> None:
    """Wyłącza kolory, np. na czarno-białym wydruku."""
    konsola.no_color = True


def pokaz_naglowek() -> None:
    """Wypisuje tytuł i krótką instrukcję."""
    konsola.print(
        Panel.fit(
            f"Słowo „{SLOWO_ANULUJ}” w dowolnym polu przerywa operację.",
            title=NAZWA_APLIKACJI,
            border_style="yellow",
        )
    )


def pokaz_menu(tytul: str, pozycje: dict[str, str]) -> None:
    """Wypisuje menu w ramce."""
    wiersze = "\n".join(f"{klucz}. {etykieta}" for klucz, etykieta in pozycje.items())
    print()
    konsola.print(Panel.fit(Text(wiersze), title=tytul, border_style="blue", padding=(0, 2)))


def sukces(tekst: str) -> None:
    """Wypisuje potwierdzenie wykonanej operacji."""
    konsola.print(Text(f"  {tekst}", style="green"), soft_wrap=True)


def ostrzezenie(tekst: str) -> None:
    """Wypisuje ostrzeżenie."""
    konsola.print(Text(f"  ! {tekst}", style="yellow"), soft_wrap=True)


def blad(tekst: str) -> None:
    """Wypisuje komunikat o błędzie."""
    konsola.print(Text(f"  ! {tekst}", style="red"), soft_wrap=True)


def _tabela(*kolumny: tuple[str, str]) -> Table:
    """Tworzy tabelę z kolumn podanych jako pary (nazwa, wyrównanie)."""
    tabela = Table(box=box.SIMPLE_HEAD)
    for nazwa, wyrownanie in kolumny:
        tabela.add_column(nazwa, justify=wyrownanie, no_wrap=wyrownanie == "right")
    return tabela


def _pasek(procent: float, kolor: str, dlugosc: int = 20) -> Text:
    """Zwraca poziomy pasek: 100 procent to pełna długość."""
    pelne = round(procent / 100 * dlugosc)
    if procent > 0:
        pelne = max(1, pelne)
    return Text("█" * pelne, kolor)


def _kwota(kwota: Decimal) -> Text:
    """Zwraca kwotę, ujemną na czerwono."""
    return Text(formatuj_kwote(kwota), style="red" if kwota < 0 else "")


def pokaz_kwoty(kwoty: dict[str, Decimal]) -> None:
    """Wypisuje nazwy i kwoty w dwóch kolumnach."""
    tabela = _tabela(("Pozycja", "left"), ("Kwota", "right"))
    for nazwa, kwota in kwoty.items():
        tabela.add_row(Text(nazwa), _kwota(kwota))
    konsola.print(tabela)


def pokaz_transakcje(
    transakcje: list[Transakcja], nazwy_kont: dict[int, str], nazwy_kategorii: dict[int, str]
) -> None:
    """Wypisuje transakcje z nazwami kont i kategorii."""
    tabela = _tabela(
        ("Nr", "right"),
        ("Data", "right"),
        ("Kwota", "right"),
        ("Opis", "left"),
        ("Konto", "left"),
        ("Kategoria", "left"),
    )
    for t in transakcje:
        tabela.add_row(
            str(t.id or "-"),
            formatuj_date(t.data),
            Text(t.ZNAK + formatuj_kwote(t.kwota), style=KOLORY_RODZAJOW[t.RODZAJ]),
            Text(t.opis_z_waluta),
            Text(nazwy_kont[t.konto_id]),
            Text(nazwy_kategorii.get(t.kategoria_id, "przelew")),
        )
    konsola.print(tabela)


def pokaz_bledy(bledy: list[str], ile: int = 10) -> None:
    """Wypisuje pierwsze błędy z listy."""
    for tekst in bledy[:ile]:
        blad(tekst)
    if len(bledy) > ile:
        blad(f"Pozostałe błędy: {len(bledy) - ile}")


def pokaz_konta(salda: list[tuple[Konto, Decimal]], razem: Decimal) -> None:
    """Wypisuje konta z saldami i saldo łączne."""
    tabela = _tabela(("Konto", "left"), ("Typ", "left"), ("Saldo", "right"))
    for konto, saldo in salda:
        tabela.add_row(Text(konto.nazwa), str(konto.typ), _kwota(saldo))
    tabela.add_section()
    tabela.add_row("Razem", "", _kwota(razem))
    konsola.print(tabela)


def pokaz_udzialy(kwoty: dict[str, Decimal], procenty: dict[str, float]) -> None:
    """Wypisuje kategorie z kwotą, procentem i paskiem."""
    tabela = _tabela(("Kategoria", "left"), ("Kwota", "right"), ("Udział", "right"), ("", "left"))
    for nazwa, kwota in kwoty.items():
        procent = procenty[nazwa]
        tabela.add_row(
            Text(nazwa), _kwota(kwota), formatuj_procent(procent), _pasek(procent, "yellow")
        )
    konsola.print(tabela)


def pokaz_budzety(wykonanie: list[WykonanieBudzetu]) -> None:
    """Wypisuje limity, wydatki i paski wykorzystania."""
    tabela = _tabela(
        ("Kategoria", "left"),
        ("Wydano", "right"),
        ("Limit", "right"),
        ("%", "right"),
        ("", "left"),
        ("Stan", "left"),
    )
    for w in wykonanie:
        kolor = KOLORY_BUDZETU[w.stan]
        tabela.add_row(
            Text(w.kategoria),
            _kwota(w.wydano),
            _kwota(w.budzet.limit),
            formatuj_procent(w.procent),
            _pasek(min(w.procent, 100), kolor, dlugosc=12),
            Text(str(w.stan), kolor),
        )
    konsola.print(tabela)


def pokaz_cele(cele: list[Cel], dzis: date) -> None:
    """Wypisuje postęp celów i potrzebną miesięczną ratę."""
    tabela = _tabela(
        ("Cel", "left"),
        ("Odłożono", "right"),
        ("Z kwoty", "right"),
        ("Termin", "right"),
        ("%", "right"),
        ("Miesięcznie", "right"),
    )
    for cel in cele:
        kolor = "green" if cel.brakuje == 0 else "red" if cel.termin < dzis else ""
        tabela.add_row(
            Text(cel.nazwa, kolor),
            _kwota(cel.odlozono),
            _kwota(cel.kwota_docelowa),
            formatuj_date(cel.termin),
            formatuj_procent(cel.procent),
            "osiągnięty" if cel.brakuje == 0 else formatuj_kwote(cel.rata(dzis)),
        )
    konsola.print(tabela)


def pokaz_osoby(grupy: list[GrupaStalych], razem: BilansStalych) -> None:
    """Wypisuje przychody, opłaty i kwotę na czysto każdej osoby."""
    tabela = _tabela(
        ("Osoba", "left"),
        ("Przychody", "right"),
        ("Opłaty", "right"),
        ("W tym wspólne", "right"),
        ("Na czysto", "right"),
    )
    osoby = [grupa for grupa in grupy if grupa.osoba_id is not None]
    wiersze = [(g.nazwa, g.bilans, policz_bilans(g.wspolne)) for g in osoby]
    wspolne = policz_bilans(u for g in osoby for u in g.wspolne)
    for nazwa, bilans, czesc in [*wiersze, ("Razem", razem, wspolne)]:
        if bilans is razem:
            tabela.add_section()
        tabela.add_row(
            Text(nazwa),
            _kwota(bilans.przychody),
            _kwota(bilans.wydatki),
            _kwota(czesc.na_czysto),
            _kwota(bilans.na_czysto),
        )
    konsola.print(tabela)
    print("  Wspólne są podzielone po równo między osoby.")


def pokaz_cykliczne(grupy: list[GrupaStalych]) -> None:
    """Wypisuje stałe pozycje. Przy kilku osobach każda ma swój nagłówek."""
    tabela = _tabela(
        ("Nazwa", "left"),
        ("Kwota", "right"),
        ("Powtarzanie", "left"),
        ("Miesięcznie", "right"),
        ("Następny termin", "right"),
    )
    for grupa in grupy:
        if len(grupy) > 1:
            tabela.add_section()
            tabela.add_row(Text(grupa.nazwa, "bold"))
        for u in grupa.udzialy:
            c = u.cykliczna
            tabela.add_row(
                Text(f"{c.nazwa} ({u.ulamek})" if u.wspolny else c.nazwa),
                _kwota(u.wplyw),
                c.powtarzanie + (" *" if c.zmienna else ""),
                _kwota(u.miesiecznie),
                formatuj_date(c.nastepny) if c.aktywna else "wyłączona",
            )
    konsola.print(tabela)
    if any(u.cykliczna.zmienna for grupa in grupy for u in grupa.udzialy):
        print("  * za każdym razem inna kwota, tu ostatnio wpisana")


def pokaz_harmonogram(platnosci: list[Platnosc], opisz: Callable[[Cykliczna], str]) -> None:
    """Wypisuje terminy stałych płatności i ich stan."""
    tabela = _tabela(
        ("Termin", "right"), ("Nazwa", "left"), ("Kwota", "right"), ("Stan", "left")
    )
    for p in platnosci:
        tabela.add_row(
            formatuj_date(p.termin),
            Text(opisz(p.cykliczna)),
            _kwota(p.wplyw),
            Text(str(p.stan), KOLORY_PLATNOSCI[p.stan]),
        )
    konsola.print(tabela)


def pokaz_trend(wiersze: list[tuple[date, dict[str, Decimal]]]) -> None:
    """Wypisuje przychody, wydatki i bilans kolejnych miesięcy."""
    kolumny = ("Przychody", "Wydatki", "Bilans")
    tabela = _tabela(("Miesiąc", "left"), *((nazwa, "right") for nazwa in kolumny))
    for miesiac, sumy in wiersze:
        tabela.add_row(formatuj_miesiac(miesiac), *(_kwota(sumy[nazwa]) for nazwa in kolumny))
    konsola.print(tabela)
