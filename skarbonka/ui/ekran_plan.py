"""Ekrany planowania: budżety."""

from skarbonka.models.transakcja import Wydatek
from skarbonka.ui import widoki
from skarbonka.ui.menu import Ekran, OpcjaMenu
from skarbonka.ui.wejscie import potwierdz, wczytaj_kwote, wczytaj_miesiac, wybierz


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


class EkranPlanu(Ekran):
    """Wejście do ekranów planowania."""

    TYTUL = "Plan"

    def opcje(self) -> list[OpcjaMenu]:
        return [
            OpcjaMenu("Budżety", EkranBudzetow(self.serwisy).uruchom),
        ]
