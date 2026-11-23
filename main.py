"""Punkt startowy aplikacji Skarbonka."""

import sys

from skarbonka.ui.aplikacja import uruchom


def main() -> None:
    """Uruchamia aplikację i pilnuje spokojnego zakończenia programu.

    Znaki, których konsola nie potrafi wyświetlić, są zastępowane, dzięki
    czemu program działa także ze starszymi kodowaniami Windows.
    """
    sys.stdout.reconfigure(errors="replace")
    try:
        uruchom()
    except (KeyboardInterrupt, EOFError):
        print("\nZakończono na życzenie użytkownika.")
    else:
        print("\nDo zobaczenia!")


if __name__ == "__main__":
    main()
