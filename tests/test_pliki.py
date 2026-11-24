"""Testy plików CSV i JSON oraz profili."""

import pytest

from skarbonka.models.importy import ProfilCSV
from skarbonka.services.profile import PROFIL_SKARBONKI, SerwisProfili
from skarbonka.storage.pliki_csv import czytaj_naglowki, czytaj_wiersze, zapisz_csv
from skarbonka.storage.pliki_json import wczytaj_json, zapisz_json
from skarbonka.wyjatki import BladPliku, BladWalidacji, UszkodzonyPlik


@pytest.fixture
def plik_csv(tmp_path):
    """Zwraca funkcję, która tworzy plik CSV o podanej treści."""

    def utworz(tresc: str, kodowanie: str = "utf-8"):
        sciezka = tmp_path / "test.csv"
        sciezka.write_bytes(tresc.encode(kodowanie))
        return sciezka

    return utworz


def test_zapis_i_odczyt_csv(tmp_path):
    sciezka = tmp_path / "nowy" / "test.csv"
    zapisz_csv(sciezka, ["data", "kwota", "opis"], [["2026-11-24", "-1,00", "a;b \"c\" żółć"]])
    assert list(czytaj_wiersze(sciezka, ProfilCSV("x"))) == [
        (2, {"data": "2026-11-24", "kwota": "-1,00", "opis": 'a;b "c" żółć'})
    ]


def test_naglowki_bez_wzgledu_na_wielkosc_liter(plik_csv):
    sciezka = plik_csv(" DATA ;Kwota;Opis\n1;2;3\n")
    assert next(czytaj_wiersze(sciezka, ProfilCSV("x")))[1] == {
        "data": "1",
        "kwota": "2",
        "opis": "3",
    }


def test_puste_i_krotkie_linie(plik_csv):
    sciezka = plik_csv("data;kwota;opis\n\n;;\n1;2\n")
    assert list(czytaj_wiersze(sciezka, ProfilCSV("x"))) == [(4, {"data": "1", "kwota": "2"})]


def test_profil_banku(plik_csv):
    sciezka = plik_csv("Wyciąg\n\nDzień,Suma,Tytuł\n1,2,Łódź\n", "cp1250")
    profil = ProfilCSV("Bank", ",", "cp1250", 2, "Dzień", "Suma", "Tytuł")
    assert czytaj_naglowki(sciezka, profil) == ["Dzień", "Suma", "Tytuł"]
    assert list(czytaj_wiersze(sciezka, profil)) == [
        (4, {"dzień": "1", "suma": "2", "tytuł": "Łódź"})
    ]


@pytest.mark.parametrize(
    ("tresc", "kodowanie"),
    [("", "utf-8"), ("a;b\n1;2\n", "utf-8"), ("data;kwota;opis\n1;2;żółć\n", "cp1250")],
)
def test_uszkodzony_csv(plik_csv, tresc, kodowanie):
    with pytest.raises(UszkodzonyPlik):
        list(czytaj_wiersze(plik_csv(tresc, kodowanie), ProfilCSV("x")))


def test_brak_pliku_i_katalog_zamiast_pliku(tmp_path):
    for sciezka in (tmp_path / "brak.csv", tmp_path):
        with pytest.raises(BladPliku):
            list(czytaj_wiersze(sciezka, ProfilCSV("x")))
    with pytest.raises(BladPliku):
        zapisz_csv(tmp_path, ["a"], [])


def test_zapis_i_odczyt_json(tmp_path):
    sciezka = tmp_path / "nowy" / "test.json"
    zapisz_json(sciezka, {"klucz": ["żółć", 1, None]})
    assert wczytaj_json(sciezka) == {"klucz": ["żółć", 1, None]}
    assert [p.name for p in sciezka.parent.iterdir()] == ["test.json"]


@pytest.mark.parametrize("tresc", [b"", b"{", b"\xff\xfe\x00", b"[1, 2"])
def test_uszkodzony_json(tmp_path, tresc):
    sciezka = tmp_path / "zly.json"
    sciezka.write_bytes(tresc)
    with pytest.raises(UszkodzonyPlik):
        wczytaj_json(sciezka)


def test_brak_pliku_json(tmp_path):
    with pytest.raises(BladPliku):
        wczytaj_json(tmp_path / "brak.json")


def test_dodanie_i_usuniecie_profilu(tmp_path):
    serwis = SerwisProfili(tmp_path / "profile.json")
    profil = ProfilCSV("Bank", separator=",")
    serwis.dodaj(profil)
    assert serwis.wszystkie() == [PROFIL_SKARBONKI, profil]
    with pytest.raises(BladWalidacji):
        serwis.dodaj(ProfilCSV("BANK"))
    serwis.usun(profil)
    assert serwis.wlasne() == []


@pytest.mark.parametrize("tresc", ["5", "null", '["x"]', '[{"nazwa": 1}]', '[{"obce": "x"}]'])
def test_uszkodzone_profile(tmp_path, tresc):
    plik = tmp_path / "profile.json"
    plik.write_text(tresc, encoding="utf-8")
    with pytest.raises(UszkodzonyPlik):
        SerwisProfili(plik).wszystkie()


def test_nie_mozna_zapisac(tmp_path):
    przeszkoda = tmp_path / "plik"
    przeszkoda.write_text("", encoding="utf-8")
    with pytest.raises(BladPliku):
        zapisz_csv(przeszkoda / "a.csv", ["a"], [])
    with pytest.raises(BladPliku):
        zapisz_json(przeszkoda / "a.json", {})


def test_nieudany_zapis_json_zostawia_stary_plik(tmp_path):
    sciezka = tmp_path / "dane.json"
    zapisz_json(sciezka, {"wersja": 1})
    with pytest.raises(BladPliku):
        zapisz_json(sciezka, {"wersja": float("nan"), "zbior": {1, 2}})
    assert wczytaj_json(sciezka) == {"wersja": 1}


def test_bledny_separator_i_kodowanie_profilu(plik_csv):
    sciezka = plik_csv("data;kwota;opis\n1;2;3\n")
    for profil in (ProfilCSV("x", separator=""), ProfilCSV("x", kodowanie="nieznane")):
        with pytest.raises(BladPliku):
            list(czytaj_wiersze(sciezka, profil))
