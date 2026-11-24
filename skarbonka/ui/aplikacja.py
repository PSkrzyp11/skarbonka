"""Główna klasa interfejsu: łączy ekrany w menu główne."""

from skarbonka.services.zestaw import Serwisy
from skarbonka.ui import widoki
from skarbonka.ui.ekran_analizy import EkranAnaliz
from skarbonka.ui.ekran_dane import EkranDanych
from skarbonka.ui.ekran_plan import EkranPlanu
from skarbonka.ui.ekran_transakcje import EkranTransakcji
from skarbonka.ui.ekran_ustawienia import EkranUstawien
from skarbonka.ui.menu import Menu, OpcjaMenu


class Aplikacja:
    """Menu główne aplikacji."""

    def __init__(self, serwisy: Serwisy) -> None:
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
        """Pokazuje nagłówek i oddaje sterowanie menu głównemu."""
        widoki.pokaz_naglowek()
        self.menu.uruchom()
