"""Tworzy skróty i polecenia, dzięki którym Skarbonka działa jak zwykła aplikacja.

Uruchomienie z opcją --usun kasuje wszystko, co utworzył ten skrypt. Dane
użytkownika zostają nietknięte.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from skarbonka.config import KATALOG_PROJEKTU, NAZWA_APLIKACJI, PLIK_IKONY

PLIK_STARTOWY = KATALOG_PROJEKTU / "main.py"
POLECENIE_OKNA = "skarbonka.cmd"
POLECENIE_KONSOLI = "skarbonka-konsola.cmd"

SKRYPT_SKROTU = """
$skrot = (New-Object -ComObject WScript.Shell).CreateShortcut($env:SKARBONKA_SKROT)
$skrot.TargetPath = $env:SKARBONKA_CEL
$skrot.Arguments = $env:SKARBONKA_ARGUMENTY
$skrot.WorkingDirectory = $env:SKARBONKA_KATALOG
$skrot.IconLocation = $env:SKARBONKA_IKONA
$skrot.Save()
"""


def python_bez_konsoli() -> Path:
    """Zwraca program, który uruchamia okno bez czarnej konsoli w tle."""
    return Path(sys.executable).with_name("pythonw.exe")


def tresc_polecen() -> dict[str, str]:
    """Zwraca nazwy i treść plików z poleceniami."""
    return {
        POLECENIE_OKNA: f'@start "" "{python_bez_konsoli()}" "{PLIK_STARTOWY}" --okno %*\n',
        POLECENIE_KONSOLI: f'@"{sys.executable}" "{PLIK_STARTOWY}" %*\n',
    }


def utworz_polecenia(katalog: Path) -> list[Path]:
    """Zapisuje polecenia w katalogu, który Windows przeszukuje z każdego terminala."""
    pliki = []
    for nazwa, tresc in tresc_polecen().items():
        plik = katalog / nazwa
        plik.write_text(tresc, encoding="oem")
        pliki.append(plik)
    return pliki


def utworz_skrot(plik: Path) -> Path:
    """Tworzy skrót do okna aplikacji."""
    zmienne = {
        "SKARBONKA_SKROT": str(plik),
        "SKARBONKA_CEL": str(python_bez_konsoli()),
        "SKARBONKA_ARGUMENTY": f'"{PLIK_STARTOWY}" --okno',
        "SKARBONKA_KATALOG": str(KATALOG_PROJEKTU),
        "SKARBONKA_IKONA": str(PLIK_IKONY),
    }
    _powershell(SKRYPT_SKROTU, zmienne)
    return plik


def katalog_systemowy(nazwa: str) -> Path:
    """Zwraca położenie pulpitu albo menu Start."""
    return Path(_powershell(f"[Environment]::GetFolderPath('{nazwa}')").strip())


def katalog_polecen() -> Path:
    """Zwraca katalog użytkownika, który jest w zmiennej PATH."""
    return Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "WindowsApps"


def miejsca_skrotow() -> list[Path]:
    """Zwraca pliki skrótów: na pulpicie i w menu Start."""
    return [katalog_systemowy(n) / f"{NAZWA_APLIKACJI}.lnk" for n in ("Desktop", "Programs")]


def usun(pliki: list[Path]) -> list[Path]:
    """Kasuje podane pliki i zwraca te, które istniały."""
    istniejace = [plik for plik in pliki if plik.exists()]
    for plik in istniejace:
        plik.unlink()
    return istniejace


def _powershell(skrypt: str, zmienne: dict[str, str] | None = None) -> str:
    """Wykonuje skrypt PowerShell i zwraca to, co wypisał."""
    wynik = subprocess.run(
        ["powershell", "-NoProfile", "-Command", skrypt],
        env=os.environ | (zmienne or {}),
        capture_output=True,
        text=True,
        encoding="oem",
        check=True,
    )
    return wynik.stdout


def main(argumenty: list[str] | None = None) -> int:
    """Instaluje albo usuwa skróty i polecenia."""
    parser = argparse.ArgumentParser(description="Skróty i polecenia Skarbonki.")
    parser.add_argument("--usun", action="store_true", help="usuń skróty i polecenia")
    opcje = parser.parse_args(argumenty)
    if sys.platform != "win32":
        print("Skróty są dostępne tylko w systemie Windows.")
        return 1
    try:
        polecenia = katalog_polecen()
        if opcje.usun:
            pliki = usun([*miejsca_skrotow(), *(polecenia / nazwa for nazwa in tresc_polecen())])
            napis = "Usunięto"
        else:
            pliki = [utworz_skrot(plik) for plik in miejsca_skrotow()]
            pliki += utworz_polecenia(polecenia)
            napis = "Utworzono"
    except (OSError, KeyError, subprocess.CalledProcessError) as blad:
        print(f"Nie udało się: {blad}")
        return 1
    for plik in pliki:
        print(f"{napis}: {plik}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
