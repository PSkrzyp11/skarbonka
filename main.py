"""Punkt startowy aplikacji Skarbonka."""

import sys

from skarbonka.services.zestaw import utworz_serwisy
from skarbonka.ui.aplikacja import Aplikacja


def main() -> None:
    """Uruchamia aplikację i pilnuje spokojnego zakończenia programu.

    Znaki, których konsola nie potrafi wyświetlić, są zastępowane, dzięki
    czemu program działa także ze starszymi kodowaniami Windows.
    """
    sys.stdout.reconfigure(errors="replace")
    try:
        Aplikacja(utworz_serwisy()).uruchom()
    except (KeyboardInterrupt, EOFError):
        print("\nZakończono na życzenie użytkownika.")
    else:
        print("\nDo zobaczenia!")


if __name__ == "__main__":
    main()
