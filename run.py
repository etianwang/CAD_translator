"""Desktop application entry point."""
import sys

from backend.cad import configure_odafc
from desktop.launcher import run_web_app


def main() -> None:
    if "--legacy" in sys.argv:
        print("The legacy Tkinter interface has been removed.")
        return
    configure_odafc()
    run_web_app()


if __name__ == "__main__":
    main()
