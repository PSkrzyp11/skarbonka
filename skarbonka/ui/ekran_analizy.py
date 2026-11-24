"""Ekran analiz: salda, podsumowania, kategorie i trend."""

from skarbonka.services import analizy
from skarbonka.services.transakcje import bilans, suma_przychodow, suma_wydatkow
from skarbonka.ui import widoki
from skarbonka.ui.menu import Ekran, OpcjaMenu
from skarbonka.ui.wejscie import wczytaj_miesiac
from skarbonka.utils.formatowanie import formatuj_date, formatuj_miesiac, formatuj_procent


class EkranAnaliz(Ekran):
    """Przetwarzanie zebranych transakcji."""

    TYTUL = "Analizy"

    def opcje(self) -> list[OpcjaMenu]:
        return [
            OpcjaMenu("Saldo i sumy", self.pokaz_sumy),
            OpcjaMenu("Podsumowanie miesiąca", self.pokaz_miesiac),
            OpcjaMenu("Wydatki według kategorii", self.pokaz_kategorie),
            OpcjaMenu("Trend 6 miesięcy", self.pokaz_trend),
            OpcjaMenu("Największe wydatki", self.pokaz_najwieksze),
            OpcjaMenu("Prognoza salda", self.pokaz_prognoze),
        ]

    def pokaz_sumy(self) -> None:
        """Wypisuje sumy wszystkich transakcji i salda kont."""
        transakcje = self.serwisy.transakcje.wszystkie()
        widoki.pokaz_kwoty(
            {
                "Przychody": suma_przychodow(transakcje),
                "Wydatki": suma_wydatkow(transakcje),
                "Bilans": bilans(transakcje),
            }
        )
        print()
        konta = self.serwisy.konta
        widoki.pokaz_konta([(k, konta.saldo(k.id)) for k in konta.wszystkie()], konta.saldo())

    def pokaz_miesiac(self) -> None:
        """Wypisuje podsumowanie wybranego miesiąca."""
        miesiac = wczytaj_miesiac()
        transakcje = self.serwisy.transakcje.wszystkie()
        liczba = len(analizy.z_miesiaca(transakcje, miesiac))
        print(f"{formatuj_miesiac(miesiac).capitalize()}, transakcje: {liczba}")
        sumy = analizy.podsumowanie_miesiaca(transakcje, miesiac)
        widoki.pokaz_kwoty(sumy)
        stopa = analizy.stopa_oszczednosci(sumy["Przychody"], sumy["Bilans"])
        if stopa is not None:
            print(f"Zaoszczędzono {formatuj_procent(stopa)} przychodów.")

    def pokaz_kategorie(self) -> None:
        """Wypisuje udział kategorii w wydatkach miesiąca."""
        wybrane = analizy.z_miesiaca(self.serwisy.transakcje.wszystkie(), wczytaj_miesiac())
        kwoty = analizy.wydatki_wg_kategorii(wybrane, self.serwisy.kategorie.wszystkie())
        if not kwoty:
            print("Brak wydatków w tym miesiącu.")
            return
        widoki.pokaz_udzialy(kwoty, analizy.udzialy(kwoty))

    def pokaz_trend(self) -> None:
        """Wypisuje przychody, wydatki i bilans ostatnich miesięcy."""
        widoki.pokaz_trend(analizy.trend(self.serwisy.transakcje.wszystkie()))

    def pokaz_najwieksze(self) -> None:
        """Wypisuje największe wydatki."""
        wydatki = analizy.najwieksze_wydatki(self.serwisy.transakcje.wszystkie())
        if not wydatki:
            print("Brak wydatków.")
            return
        widoki.pokaz_transakcje(
            wydatki, self.serwisy.konta.nazwy(), self.serwisy.kategorie.nazwy()
        )

    def pokaz_prognoze(self) -> None:
        """Wypisuje prognozę salda na koniec miesiąca."""
        prognoza = self.serwisy.prognoza.policz()
        print(f"Do {formatuj_date(prognoza.koniec)} zostało dni: {prognoza.dni}")
        widoki.pokaz_kwoty(
            {
                "Saldo dziś": prognoza.saldo_dzis,
                "Transakcje cykliczne": prognoza.cykliczne,
                "Dzienne wydatki (średnio)": prognoza.tempo_srednie,
            }
        )
        widoki.pokaz_kwoty(
            {
                "Optymistycznie": prognoza.optymistyczna,
                "Realistycznie": prognoza.realistyczna,
                "Pesymistycznie": prognoza.pesymistyczna,
            }
        )
