"""Punkt startowy aplikacji Skarbonka."""

from skarbonka import __version__
from skarbonka.config import NAZWA_APLIKACJI


def main() -> None:
    """Uruchamia aplikację."""
    print(f"{NAZWA_APLIKACJI} {__version__}")


if __name__ == "__main__":
    main()
