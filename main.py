"""Punkt startowy aplikacji Skarbonka."""

from skarbonka.ui.aplikacja import uruchom


def main() -> None:
    """Uruchamia aplikację i pilnuje spokojnego zakończenia programu."""
    try:
        uruchom()
    except (KeyboardInterrupt, EOFError):
        print("\nZakończono na życzenie użytkownika.")
    else:
        print("\nDo zobaczenia!")


if __name__ == "__main__":
    main()
