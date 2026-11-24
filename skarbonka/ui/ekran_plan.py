"""Ekrany planowania: budżety i cele."""

from datetime import date, timedelta

from skarbonka.models.transakcja import Wydatek
from skarbonka.ui import widoki
from skarbonka.ui.menu import Ekran, OpcjaMenu
from skarbonka.ui.wejscie import (
    potwierdz,
    wczytaj_kwote,
    wczytaj_miesiac,
    wczytaj_nazwe,
    wczytaj_termin,
    wybierz,
)


class EkranBudzetow(Ekran):
    """Miesięczne limity wydatków."""

    TYTUL = "Budżety"

    def opcje(self) -> list[OpcjaMenu]:
        return [
            OpcjaMenu("Stan budżetów", self.pokaz),
            OpcjaMenu("Ustaw limit", self.ustaw),
            OpcjaMenu("Skopiuj z poprzedniego miesiąca", self.skopiuj),
            OpcjaMenu("Usuń budżet", self.usun),
        ]

    def pokaz(self) -> None:
        """Wypisuje wykonanie budżetów wybranego miesiąca."""
        wykonanie = self.serwisy.budzety.wykonanie(wczytaj_miesiac())
        if not wykonanie:
            print("Brak budżetów w tym miesiącu.")
            return
        widoki.pokaz_budzety(wykonanie)

    def ustaw(self) -> None:
        """Ustawia limit dla kategorii."""
        miesiac = wczytaj_miesiac()
        kategoria = wybierz("Kategoria", self.serwisy.kategorie.pasujace(Wydatek))
        self.serwisy.budzety.ustaw(kategoria.id, miesiac, wczytaj_kwote("Limit"))
        widoki.sukces(f"Ustawiono limit dla kategorii {kategoria.nazwa}.")

    def skopiuj(self) -> None:
        """Przenosi limity z poprzedniego miesiąca."""
        liczba = self.serwisy.budzety.skopiuj_poprzedni(wczytaj_miesiac())
        widoki.sukces(f"Skopiowane budżety: {liczba}")

    def usun(self) -> None:
        """Usuwa wybrany budżet po potwierdzeniu."""
        wykonanie = self.serwisy.budzety.wykonanie(wczytaj_miesiac())
        budzety = {w.kategoria: w.budzet for w in wykonanie}
        nazwa = wybierz("Budżet do usunięcia", list(budzety))
        if potwierdz(f"Na pewno usunąć budżet „{nazwa}”?"):
            self.serwisy.budzety.usun(budzety[nazwa])
            widoki.sukces("Usunięto.")


class EkranCeli(Ekran):
    """Cele oszczędnościowe."""

    TYTUL = "Cele oszczędnościowe"

    def opcje(self) -> list[OpcjaMenu]:
        return [
            OpcjaMenu("Postęp celów", self.pokaz),
            OpcjaMenu("Dodaj cel", self.dodaj),
            OpcjaMenu("Wpłać na cel", self.wplac),
            OpcjaMenu("Usuń cel", self.usun),
        ]

    def pokaz(self) -> None:
        """Wypisuje postęp wszystkich celów."""
        cele = self.serwisy.cele.wszystkie()
        if not cele:
            print("Brak celów.")
            return
        widoki.pokaz_cele(cele, date.today())

    def dodaj(self) -> None:
        """Wczytuje dane i dodaje cel."""
        nazwa = wczytaj_nazwe("Nazwa celu", self.serwisy.cele.sprawdz_nazwe)
        kwota = wczytaj_kwote("Kwota docelowa")
        termin = wczytaj_termin("Termin", date.today() + timedelta(days=1))
        self.serwisy.cele.dodaj(nazwa, kwota, termin)
        widoki.sukces(f"Dodano cel {nazwa}.")

    def wplac(self) -> None:
        """Dopisuje wpłatę do wybranego celu."""
        cel = wybierz("Cel", self.serwisy.cele.wszystkie())
        self.serwisy.cele.wplac(cel, wczytaj_kwote("Wpłata"))
        self.pokaz()

    def usun(self) -> None:
        """Usuwa wybrany cel po potwierdzeniu."""
        cel = wybierz("Cel do usunięcia", self.serwisy.cele.wszystkie())
        if potwierdz(f"Na pewno usunąć „{cel.nazwa}” i jego wpłaty?"):
            self.serwisy.cele.usun(cel)
            widoki.sukces("Usunięto.")


class EkranPlanu(Ekran):
    """Wejście do ekranów planowania."""

    TYTUL = "Plan"

    def opcje(self) -> list[OpcjaMenu]:
        return [
            OpcjaMenu("Budżety", EkranBudzetow(self.serwisy).uruchom),
            OpcjaMenu("Cele oszczędnościowe", EkranCeli(self.serwisy).uruchom),
        ]
