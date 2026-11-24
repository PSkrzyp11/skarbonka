"""Ekrany ustawień: konta i kategorie."""

from skarbonka.models.enums import TypKonta
from skarbonka.models.transakcja import Przychod, Wydatek
from skarbonka.ui import widoki
from skarbonka.ui.ekran_profile import EkranProfili
from skarbonka.ui.menu import Ekran, OpcjaMenu
from skarbonka.ui.wejscie import (
    potwierdz,
    wczytaj_liczbe,
    wczytaj_nazwe,
    wczytaj_saldo,
    wybierz,
)


class EkranKont(Ekran):
    """Zarządzanie kontami."""

    TYTUL = "Konta"

    def opcje(self) -> list[OpcjaMenu]:
        return [
            OpcjaMenu("Lista kont", self.pokaz),
            OpcjaMenu("Dodaj konto", self.dodaj),
            OpcjaMenu("Usuń konto", self.usun),
        ]

    def pokaz(self) -> None:
        """Wypisuje konta z saldami."""
        konta = self.serwisy.konta
        widoki.pokaz_konta([(k, konta.saldo(k.id)) for k in konta.wszystkie()], konta.saldo())

    def dodaj(self) -> None:
        """Wczytuje dane i dodaje konto."""
        nazwa = wczytaj_nazwe("Nazwa konta", self.serwisy.konta.sprawdz_nazwe)
        typ = wybierz("Typ konta", list(TypKonta))
        konto = self.serwisy.konta.dodaj(nazwa, typ, wczytaj_saldo())
        widoki.sukces(f"Dodano: {konto}")

    def usun(self) -> None:
        """Usuwa wybrane konto po potwierdzeniu."""
        konto = wybierz("Konto do usunięcia", self.serwisy.konta.wszystkie())
        if potwierdz(f"Na pewno usunąć „{konto.nazwa}”?"):
            self.serwisy.konta.usun(konto)
            widoki.sukces("Usunięto.")


class EkranKategorii(Ekran):
    """Zarządzanie kategoriami."""

    TYTUL = "Kategorie"

    def opcje(self) -> list[OpcjaMenu]:
        return [
            OpcjaMenu("Lista kategorii", self.pokaz),
            OpcjaMenu("Dodaj kategorię", self.dodaj),
            OpcjaMenu("Usuń kategorię", self.usun),
        ]

    def pokaz(self) -> None:
        """Wypisuje kategorie w podziale na wydatki i przychody."""
        for tytul, rodzaj in (("Wydatki", Wydatek), ("Przychody", Przychod)):
            nazwy = [k.nazwa for k in self.serwisy.kategorie.pasujace(rodzaj)]
            print(f"{tytul}: {', '.join(nazwy) or 'brak'}")

    def dodaj(self) -> None:
        """Wczytuje dane i dodaje kategorię."""
        nazwa = wczytaj_nazwe("Nazwa kategorii", self.serwisy.kategorie.sprawdz_nazwe)
        czy_wydatek = potwierdz("Czy to kategoria wydatków?")
        self.serwisy.kategorie.dodaj(nazwa, czy_wydatek)
        widoki.sukces(f"Dodano: {nazwa}")

    def usun(self) -> None:
        """Usuwa wybraną kategorię po potwierdzeniu."""
        kategoria = wybierz("Kategoria do usunięcia", self.serwisy.kategorie.wszystkie())
        if potwierdz(f"Na pewno usunąć „{kategoria.nazwa}”?"):
            self.serwisy.kategorie.usun(kategoria)
            widoki.sukces("Usunięto.")


class EkranUstawien(Ekran):
    """Wejście do pozostałych ustawień."""

    TYTUL = "Ustawienia"

    def opcje(self) -> list[OpcjaMenu]:
        return [
            OpcjaMenu("Konta", EkranKont(self.serwisy).uruchom),
            OpcjaMenu("Kategorie", EkranKategorii(self.serwisy).uruchom),
            OpcjaMenu("Profile CSV banków", EkranProfili(self.serwisy).uruchom),
            OpcjaMenu("Próg ostrzeżeń budżetu", self.zmien_prog),
        ]

    def zmien_prog(self) -> None:
        """Zmienia procent budżetu, od którego pojawia się ostrzeżenie."""
        ustawienia = self.serwisy.ustawienia.wczytaj()
        ustawienia.prog_ostrzezen = wczytaj_liczbe(
            "Próg w procentach", maks=100, domyslna=ustawienia.prog_ostrzezen, minimum=1
        )
        self.serwisy.ustawienia.zapisz(ustawienia)
        widoki.sukces(f"Próg ostrzeżeń: {ustawienia.prog_ostrzezen}%")
