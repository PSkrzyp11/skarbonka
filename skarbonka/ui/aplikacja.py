"""Główna klasa interfejsu: pulpit i menu główne."""

from datetime import date

from skarbonka.services.uwagi import zbierz_uwagi
from skarbonka.services.zestaw import Serwisy
from skarbonka.ui import widoki
from skarbonka.ui.ekran_analizy import EkranAnaliz
from skarbonka.ui.ekran_dane import EkranDanych
from skarbonka.ui.ekran_plan import EkranPlanu
from skarbonka.ui.ekran_transakcje import EkranTransakcji
from skarbonka.ui.ekran_ustawienia import EkranUstawien
from skarbonka.ui.menu import Menu, OpcjaMenu
from skarbonka.utils.formatowanie import formatuj_kwote


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
        konta = self.serwisy.konta
        widoki.pokaz_konta([(k, konta.saldo(k.id)) for k in konta.wszystkie()], konta.saldo())
        bilans = self.serwisy.cykliczne.bilans()
        if bilans.przychody or bilans.wydatki:
            print(f"  Na czysto co miesiąc: {formatuj_kwote(bilans.na_czysto)}")
        for uwaga in zbierz_uwagi(self.serwisy, dzis):
            widoki.ostrzezenie(str(uwaga))
