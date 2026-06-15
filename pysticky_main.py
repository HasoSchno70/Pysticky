#!/usr/bin/env python
"""
PyInstaller Entry-Point fuer PySticky.

Delegiert an `pysticky.main:main`, damit es nur eine Wahrheit fuer
den Programmstart gibt (PyInstaller-Build, `python -m pysticky`,
`python run.py` und der `pysticky`-gui-script-Eintrag in pyproject.toml
landen alle hier).
"""

import sys
from pathlib import Path

# Src-Verzeichnis zum Pfad hinzufuegen (vor dem Import von pysticky)
_SRC = Path(__file__).parent / "src"
if _SRC.exists():
    sys.path.insert(0, str(_SRC))

from pysticky.main import main


if __name__ == "__main__":
    sys.exit(main())
