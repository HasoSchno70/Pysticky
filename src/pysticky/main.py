"""
Einstiegspunkt der PySticky Anwendung.
"""

import sys


def main() -> int:
    """
    Hauptfunktion - Einstiegspunkt der Anwendung.

    Returns:
        Exit-Code (0 = Erfolg, != 0 = Fehler)
    """
    from .app import PySticky

    app = PySticky()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
