"""Stałe przychody i opłaty: ile zostaje na czysto i co trzeba zapłacić."""

from datetime import date

import customtkinter as ctk

from skarbonka.gui import ikony, styl
from skarbonka.gui.formularz import Formularz
from skarbonka.gui.formularze_stalych import edycja_stalej, kwota_terminu, nowa_stala
from skarbonka.gui.karta_osob import NUMER_WSZYSTKICH, KartaOsob
from skarbonka.gui.lista import Lista, Naglowek, Pozycja
from skarbonka.gui.pozycje import kwota_ze_znakiem
from skarbonka.gui.skladniki import (
    Karta,
    Przewijana,
    etykieta,
    kafelek_ikony,
    pasek_postepu,
    przycisk,
    przycisk_ikony,
    pusty_stan,
    ramka,
    wyczysc,
)
from skarbonka.gui.widok import Widok
from skarbonka.models.cykliczna import Cykliczna
from skarbonka.models.enums import Czestotliwosc, StanPlatnosci
from skarbonka.models.transakcja import Przychod, Wydatek
from skarbonka.services.cykliczne import BilansStalych, Platnosc, do_zaplaty, policz_bilans
from skarbonka.services.uwagi import STALE
from skarbonka.utils.formatowanie import (
    formatuj_date,
    formatuj_kwote,
    formatuj_miesiac,
    formatuj_procent,
)
from skarbonka.wyjatki import NieZnalezionoRekordu

SZEROKOSC_BOCZNA = 370
NA_CZYSTO = "Na czysto co miesiąc"
NAJWIECEJ_PLATNOSCI = 20

WYGLAD_STANOW = {
    StanPlatnosci.ZALATWIONA: (ikony.PTASZEK, styl.AKCENT_TLO, styl.AKCENT_TEKST),
    StanPlatnosci.CZEKA: (ikony.ZEGAR, styl.UWAGA_TLO, styl.UWAGA),
    StanPlatnosci.NADCHODZI: (ikony.KALENDARZ, styl.WGLEBIENIE, styl.TEKST_DRUGI),
}


class WidokStale(Widok):
    """Miesięczny bilans, lista stałych pozycji i płatności tego miesiąca."""

    TYTUL = STALE
    IKONA = ikony.POWTARZANIE

    def buduj(self) -> None:
        self.serwis = self.serwisy.cykliczne
        self.podtytul.configure(text="Przychody i opłaty, które się powtarzają")
        przycisk(self.pasek, "Dodaj opłatę", self.dodaj_oplate, "glowny", 130, 42).pack(
            side="right"
        )
        przycisk(self.pasek, "Dodaj przychód", self.dodaj_przychod, "zwykly", 140, 42).pack(
            side="right", padx=10
        )
        przycisk(self.pasek, "Dodaj osobę", self.dodaj_osobe, "zwykly", 120, 42).pack(side="right")
        self._siatka = ramka(self.tresc)
        self._siatka.grid_columnconfigure(0, weight=1)
        self._siatka.grid_columnconfigure(1, minsize=SZEROKOSC_BOCZNA)
        self._siatka.grid_rowconfigure(1, weight=1)
        self._buduj_bilans()
        self._buduj_liste()
        bok = ramka(self._siatka)
        bok.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(20, 0))
        self.osoby = KartaOsob(bok, self.okno, self.odswiez)
        platnosci = Karta(bok, formatuj_miesiac(date.today()).capitalize())
        platnosci.pack(side="bottom", fill="both", expand=True)
        self._do_zaplaty = etykieta(platnosci.gora, "", 13, kolor=styl.TEKST_DRUGI)
        self._do_zaplaty.pack(side="right")
        self._platnosci = Przewijana(platnosci, styl.KARTA)
        self._platnosci.pack(fill="both", expand=True, padx=(12, 6), pady=(0, 12))
        self._pusty = pusty_stan(
            self.tresc,
            ikony.POWTARZANIE,
            "Ile zostaje Ci na czysto?",
            "Wpisz stały przychód i opłaty, a Skarbonka policzy resztę.",
            ("Dodaj przychód", self.dodaj_przychod),
        )

    def _buduj_bilans(self) -> None:
        """Tworzy zieloną kartę z kwotą na czysto."""
        karta = ctk.CTkFrame(self._siatka, fg_color=styl.MARKA, corner_radius=20)
        karta.grid(row=0, column=0, sticky="nsew")
        self._czyje = etykieta(karta, NA_CZYSTO, 13, "mocny", styl.MARKA_TEKST)
        self._czyje.pack(anchor="w", padx=28, pady=(24, 0))
        self.na_czysto = etykieta(karta, "", 46, "liczby", styl.BIALY)
        self.na_czysto.pack(anchor="w", padx=28, pady=(4, 2))
        self._opis = etykieta(karta, "", 13, kolor=styl.MARKA_TEKST)
        self._opis.pack(anchor="w", padx=28)
        self._szczegoly = ramka(karta)
        self._szczegoly.pack(fill="x", padx=28, pady=(16, 24))

    def _buduj_liste(self) -> None:
        """Tworzy listę pozycji z akcjami dla zaznaczonej."""
        karta = Karta(self._siatka)
        karta.grid(row=1, column=0, sticky="nsew", pady=(20, 0))
        self._akcje = ctk.CTkFrame(karta, fg_color=styl.AKCENT_TLO, corner_radius=12)
        przycisk_ikony(self._akcje, ikony.KOSZ, self.usun, "grozny", 34).pack(
            side="right", padx=8, pady=8
        )
        self._przelacznik = przycisk(self._akcje, "", self.przelacz, "glowny", 80, 34)
        self._przelacznik.pack(side="right")
        przycisk(self._akcje, "Edytuj", self.edytuj, "glowny", 80, 34).pack(side="right", padx=8)
        self._nazwa_wybranej = etykieta(self._akcje, "", 13, "mocny", styl.AKCENT_TEKST)
        self._nazwa_wybranej.pack(side="left", padx=18)
        self.tabela = Lista(karta, self._wybrano, self.edytuj)
        self.tabela.pack(fill="both", expand=True, padx=10, pady=12)

    def odswiez(self) -> None:
        stale = self.serwis.wszystkie()
        self._sa_osoby = bool(self.serwisy.osoby.wszystkie())
        if not stale and not self._sa_osoby:
            self._siatka.pack_forget()
            self._pusty.pack(expand=True)
            return
        self._pusty.pack_forget()
        self._siatka.pack(fill="both", expand=True)
        self._pokaz_osoby()
        stale = [c for c in stale if self.osoby.pasuje(c)]
        bilans = policz_bilans(stale)
        self._pokaz_bilans(bilans)
        self.tabela.wypelnij(self._pozycje(stale, bilans))
        self._wybrano()
        self._pokaz_platnosci()

    def _pokaz_osoby(self) -> None:
        """Pokazuje kartę osób, o ile jakieś są."""
        self.osoby.odswiez()
        if self._sa_osoby:
            self.osoby.pack(side="top", fill="x", pady=(0, 20))
        else:
            self.osoby.pack_forget()
        jedna = self.osoby.wybrana != NUMER_WSZYSTKICH
        self._czyje.configure(
            text=f"{NA_CZYSTO}  ·  {self.osoby.nazwa_wybranej()}" if jedna else NA_CZYSTO
        )

    def _pokaz_bilans(self, bilans: BilansStalych) -> None:
        """Wypełnia zieloną kartę."""
        self.na_czysto.configure(text=kwota_ze_znakiem(formatuj_kwote(bilans.na_czysto)))
        if bilans.procent is None:
            opis = "Dodaj stały przychód, żeby zobaczyć, ile zostaje"
        elif bilans.na_czysto < 0:
            opis = "Opłaty są wyższe niż stałe przychody"
        else:
            procent, dziennie = formatuj_procent(bilans.procent), formatuj_kwote(bilans.dziennie)
            opis = f"{procent} przychodów, czyli {dziennie} na dzień"
        self._opis.configure(text=opis)
        wyczysc(self._szczegoly)
        udzial = 100.0 if bilans.procent is None else 100 - bilans.procent
        pasek_postepu(self._szczegoly, udzial, styl.MOSIADZ, styl.MARKA_WYBRANA).pack(
            fill="x", pady=(0, 12)
        )
        for strona, bok, nazwa, kwota in (
            ("left", "w", "Opłaty", bilans.wydatki),
            ("right", "e", "Przychody", bilans.przychody),
        ):
            kolumna = ramka(self._szczegoly)
            kolumna.pack(side=strona)
            etykieta(kolumna, nazwa, 12, kolor=styl.MARKA_TEKST).pack(anchor=bok)
            etykieta(kolumna, formatuj_kwote(kwota), 18, "liczby", styl.BIALY).pack(anchor=bok)

    def _pozycje(self, stale: list[Cykliczna], bilans: BilansStalych) -> list[Pozycja | Naglowek]:
        """Zwraca pozycje w dwóch grupach, od najwyższej kwoty miesięcznej."""
        wynik: list[Pozycja | Naglowek] = []
        for nazwa, rodzaj, suma in (
            ("Przychody", Przychod.RODZAJ, bilans.przychody),
            ("Opłaty", Wydatek.RODZAJ, bilans.wydatki),
        ):
            grupa = [c for c in stale if c.rodzaj == rodzaj]
            if grupa:
                wynik.append(Naglowek(nazwa, f"{formatuj_kwote(suma)} miesięcznie"))
            grupa.sort(key=lambda c: (not c.aktywna, -abs(c.miesiecznie)))
            wynik.extend(self._pozycja(c) for c in grupa)
        return wynik

    def _pozycja(self, stala: Cykliczna) -> Pozycja:
        """Zamienia stałą pozycję na element listy."""
        kategoria = self.serwisy.kategorie.nazwy().get(stala.kategoria_id, "")
        ikona = ikony.dla_nazwy(stala.nazwa, ikony.dla_nazwy(kategoria, ikony.POWTARZANIE))
        if stala.aktywna:
            stan = f"termin {formatuj_date(stala.nastepny)}"
            kolor = styl.DOBRY if stala.wplyw > 0 else styl.TEKST
        else:
            stan, kolor = "wyłączona", styl.TEKST_DRUGI
        return Pozycja(
            stala.id,
            ikona,
            stala.nazwa,
            f"{stala.czestotliwosc}  ·  {stan}{self._czyja(stala)}",
            kwota_ze_znakiem(formatuj_kwote(stala.wplyw)),
            self._podpis(stala),
            kolor,
            wyrozniona=stala.aktywna and stala.wplyw > 0,
        )

    def _podpis(self, stala: Cykliczna) -> str:
        """Zwraca podpis pod kwotą: średnią zmiennej albo przeliczenie na miesiąc."""
        if stala.zmienna:
            srednia = self.serwis.srednia(stala)
            return "kwota zmienna" if srednia is None else f"średnio {formatuj_kwote(srednia)}"
        if stala.czestotliwosc is Czestotliwosc.MIESIAC:
            return ""
        return f"{kwota_ze_znakiem(formatuj_kwote(stala.miesiecznie))} na miesiąc"

    def _czyja(self, stala: Cykliczna) -> str:
        """Zwraca dopisek z imieniem, gdy widać pozycje wszystkich osób."""
        if stala.osoba_id is None or self.osoby.wybrana != NUMER_WSZYSTKICH:
            return ""
        return f"  ·  {self.serwisy.osoby.pobierz(stala.osoba_id)}"

    def _pokaz_platnosci(self) -> None:
        """Wypisuje terminy z tego miesiąca i starsze zaległości."""
        wyczysc(self._platnosci)
        platnosci = [p for p in self.serwis.harmonogram() if self.osoby.pasuje(p.cykliczna)]
        zostalo = do_zaplaty(platnosci)
        if zostalo:
            stan = f"do zapłaty {formatuj_kwote(zostalo)}"
        else:
            stan = "wszystko opłacone" if platnosci else ""
        self._do_zaplaty.configure(text=stan)
        for platnosc in platnosci[:NAJWIECEJ_PLATNOSCI]:
            self._dodaj_platnosc(platnosc)
        reszta = len(platnosci) - NAJWIECEJ_PLATNOSCI
        if reszta > 0:
            self._dodaj_napis(f"Kolejne terminy: {reszta}")
        if not platnosci:
            self._dodaj_napis("W tym miesiącu nic nie przypada.")

    def _dodaj_napis(self, tekst: str) -> None:
        """Dodaje szary napis w karcie płatności."""
        etykieta(self._platnosci, tekst, kolor=styl.TEKST_DRUGI).pack(anchor="w", padx=4, pady=8)

    def _dodaj_platnosc(self, platnosc: Platnosc) -> None:
        """Dodaje jeden termin. Przyciski ma tylko najbliższy termin każdej pozycji."""
        stala, termin, stan = platnosc.cykliczna, platnosc.termin, platnosc.stan
        ikona, tlo, kolor = WYGLAD_STANOW[stan]
        gotowa = stan is StanPlatnosci.ZALATWIONA
        rzad = ramka(self._platnosci)
        rzad.pack(fill="x", pady=(8, 2))
        kafelek_ikony(rzad, ikona, tlo, kolor, bok=36).pack(side="left", padx=(4, 12))
        etykieta(
            rzad,
            kwota_ze_znakiem(formatuj_kwote(platnosc.wplyw)),
            15,
            "liczby",
            styl.TEKST_DRUGI if gotowa else styl.TEKST,
        ).pack(side="right", padx=(8, 14))
        napisy = ramka(rzad)
        napisy.pack(side="left", fill="x", expand=True)
        nazwa = etykieta(napisy, self.serwis.opis(stala), 14, "mocny")
        nazwa.configure(wraplength=SZEROKOSC_BOCZNA - 210)
        nazwa.pack(anchor="w")
        etykieta(napisy, f"{formatuj_date(termin)}  ·  {stan}", 12, kolor=styl.TEKST_DRUGI).pack(
            anchor="w"
        )
        if platnosc.kolejna or platnosc.do_poprawy:
            self._dodaj_przyciski(platnosc)

    def _dodaj_przyciski(self, platnosc: Platnosc) -> None:
        """Dodaje przyciski pod terminem."""
        stala, termin = platnosc.cykliczna, platnosc.termin
        czeka = platnosc.stan is StanPlatnosci.CZEKA
        if platnosc.do_poprawy:
            napis = "Popraw kwotę"
        elif stala.zmienna:
            napis = "Wpisz kwotę"
        else:
            napis = "Zaksięguj" if czeka else "Zaksięguj wcześniej"
        rzad = ramka(self._platnosci)
        rzad.pack(fill="x", padx=(52, 0), pady=(4, 6))
        wyglad = "glowny" if czeka else "zwykly"
        przycisk(rzad, napis, lambda: self.zalatw(platnosc), wyglad, 100, 30).pack(side="left")
        if platnosc.kolejna:
            przycisk(rzad, "Pomiń", lambda: self.pomin(stala, termin), "cichy", 70, 30).pack(
                side="left", padx=6
            )

    def _wybrano(self) -> None:
        """Pokazuje przyciski dla zaznaczonej pozycji."""
        if self.tabela.zaznaczony() is None:
            self._akcje.pack_forget()
            return
        stala = self.wybrana()
        self._nazwa_wybranej.configure(text=stala.nazwa)
        self._przelacznik.configure(text="Wyłącz" if stala.aktywna else "Włącz")
        self._akcje.pack(side="bottom", fill="x", padx=12, pady=(0, 12), before=self.tabela)

    def wybrana(self) -> Cykliczna:
        """Zwraca zaznaczoną pozycję."""
        numer = self.tabela.zaznaczony()
        if numer is None:
            raise NieZnalezionoRekordu("Najpierw zaznacz pozycję na liście.")
        return self.serwis.pobierz(numer)

    def dodaj_przychod(self) -> Formularz:
        """Otwiera panel stałego przychodu."""
        return nowa_stala(self.okno, Przychod, self.osoby.osoba_id())

    def dodaj_oplate(self) -> Formularz:
        """Otwiera panel stałej opłaty."""
        return nowa_stala(self.okno, Wydatek, self.osoby.osoba_id())

    def dodaj_osobe(self) -> Formularz:
        """Otwiera panel nowej osoby."""
        return self.osoby.dodaj()

    def edytuj(self) -> Formularz:
        """Otwiera panel zmiany zaznaczonej pozycji."""
        return edycja_stalej(self.okno, self.wybrana())

    def przelacz(self) -> None:
        """Włącza albo wyłącza zaznaczoną pozycję."""
        zmieniona = self.serwis.przelacz(self.wybrana())
        self.okno.powiadom(f"{zmieniona}: {'włączona' if zmieniona.aktywna else 'wyłączona'}")
        self.okno.odswiez()

    def usun(self) -> None:
        """Usuwa zaznaczoną pozycję po potwierdzeniu."""
        stala = self.wybrana()
        pytanie = f"Usunąć „{stala}”? Zaksięgowane transakcje zostaną."
        if self.okno.zapytaj(pytanie, "Usuń", grozne=True):
            self.serwis.usun(stala)
            self.okno.powiadom("Usunięto.")
            self.okno.odswiez()

    def zalatw(self, platnosc: Platnosc) -> None:
        """Księguje stałą kwotę, a o zmienną najpierw pyta."""
        if platnosc.cykliczna.zmienna:
            self.wpisz_kwote(platnosc)
        else:
            self.zaksieguj(platnosc.cykliczna, platnosc.termin)

    def wpisz_kwote(self, platnosc: Platnosc) -> Formularz:
        """Otwiera panel z kwotą jednego terminu."""
        return kwota_terminu(self.okno, platnosc)

    def zaksieguj(self, stala: Cykliczna, termin: date) -> None:
        """Dodaje transakcję z podanego terminu."""
        self.serwis.zaksieguj(stala, termin)
        self.okno.powiadom(f"Zaksięgowano: {stala}")
        self.okno.odswiez()

    def pomin(self, stala: Cykliczna, termin: date) -> None:
        """Pomija termin bez dodawania transakcji."""
        self.serwis.pomin(stala, termin)
        self.okno.powiadom(f"Pominięto termin: {stala}")
        self.okno.odswiez()
