#!/usr/bin/env python
"""
Dev-Starter fuer PySticky aus dem Repo-Root.

Verwendung:
    python run.py
    .venv/Scripts/python run.py

Andere Wege ins Programm — alle landen letztlich in `pysticky.main:main`:
    py -m pysticky                       (via __main__.py)
    pip install -e .  &&  pysticky       (via pyproject [gui-scripts])
    pysticky_main.py                     (PyInstaller-Eintrag)
"""

import sys
from pathlib import Path

# Src-Verzeichnis zum Pfad hinzufuegen (vor dem Import von pysticky)
sys.path.insert(0, str(Path(__file__).parent / "src"))

from pysticky.main import main

if __name__ == "__main__":
    sys.exit(main())
