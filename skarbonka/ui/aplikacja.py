"""Główna klasa interfejsu: pulpit i menu główne."""

from datetime import date

from skarbonka.services.zestaw import Serwisy
from skarbonka.ui import widoki
from skarbonka.ui.ekran_analizy import EkranAnaliz
from skarbonka.ui.ekran_dane import EkranDanych
from skarbonka.ui.ekran_plan import EkranPlanu
from skarbonka.ui.ekran_transakcje import EkranTransakcji
from skarbonka.ui.ekran_ustawienia import EkranUstawien
from skarbonka.ui.menu import Menu, OpcjaMenu
from skarbonka.utils.formatowanie import formatuj_procent


class Aplikacja:
    """Menu główne aplikacji."""

    def __init__(self, serwisy: Serwisy) -> None:
        self.serwisy = serwisy
        ekrany = [
            EkranTransakcji(serwisy),
            EkranPlanu(serwisy),
            EkranAnaliz(serwisy),
            EkranDanych(serwisy),
            EkranUstawien(serwisy),
        ]
        self.menu = Menu(
            "Menu główne",
            [OpcjaMenu(ekran.TYTUL, ekran.uruchom) for ekran in ekrany],
            powrot="Wyjście",
        )

    def uruchom(self) -> None:
        """Pokazuje nagłówek i pulpit, a potem oddaje sterowanie menu."""
        widoki.pokaz_naglowek()
        self.pokaz_pulpit()
        self.menu.uruchom()

    def pokaz_pulpit(self, dzis: date | None = None) -> None:
        """Wypisuje salda i sprawy, które wymagają uwagi."""
        dzis = dzis or date.today()
        konta = self.serwisy.konta
        widoki.pokaz_konta([(k, konta.saldo(k.id)) for k in konta.wszystkie()], konta.saldo())
        for w in self.serwisy.budzety.ostrzezenia(dzis):
            widoki.ostrzezenie(
                f"Budżet {w.kategoria}: {w.stan}, wykorzystano {formatuj_procent(w.procent)}."
            )
        zalegle = len(self.serwisy.cykliczne.zalegle(dzis))
        if zalegle:
            widoki.ostrzezenie(f"Zaległe transakcje cykliczne: {zalegle} (Plan -> Cykliczne).")
        for cel in self.serwisy.cele.wszystkie():
            if cel.brakuje and cel.termin < dzis:
                widoki.ostrzezenie(f"Minął termin celu {cel.nazwa}.")
