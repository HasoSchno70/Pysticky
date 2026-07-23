# -*- coding: utf-8 -*-
"""OS-übergreifendes Öffnen/Anzeigen von Dateien und Ordnern.

`os.startfile()` existiert nur unter Windows; `xdg-open` ist ein
Linux-Desktop-Kommando und auf macOS nicht vorhanden (macOS nutzt `open`
bzw. `open -R` zum Anzeigen im Finder). Eine Verzweigung, die nur
zwischen "Windows" und "sonst = xdg-open" unterscheidet, funktioniert
auf Linux, schlägt aber auf macOS lautlos fehl (Kommando nicht gefunden,
kein Fehlerdialog) -- der "Datei/Ordner öffnen"-Button nach einem Export
wäre dort komplett wirkungslos. Diese beiden Funktionen kapseln die
korrekte 3-Wege-Verzweigung (Windows/macOS/Linux) an einer Stelle.
"""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path


def open_path(path: str) -> None:
    """Öffnet eine Datei oder einen Ordner mit der Standard-Anwendung
    des Betriebssystems (Windows: Datei-Assoziation, macOS: `open`,
    Linux: `xdg-open`)."""
    system = platform.system()
    if system == "Windows":
        # os.startfile existiert nur im Windows-Zweig des typeshed-Stubs --
        # unter Linux/macOS meldet mypy hier "attr-defined", unter Windows
        # waere derselbe Ignore-Kommentar "unused" (warn_unused_ignores=true
        # in pyproject.toml). "unused-ignore" mit in der Codeliste macht den
        # Ignore-Kommentar bewusst plattform-tolerant in beide Richtungen.
        os.startfile(path)  # type: ignore[attr-defined, unused-ignore]
    elif system == "Darwin":
        subprocess.run(["open", path])
    else:
        subprocess.run(["xdg-open", path])


def reveal_in_file_manager(path: str) -> None:
    """Zeigt eine Datei im Datei-Manager an, nach Möglichkeit mit
    markierter Datei (Windows Explorer, macOS Finder). Linux hat kein
    plattformweit einheitliches "Datei markieren"-Kommando -- dort wird
    ersatzweise der enthaltende Ordner geöffnet."""
    system = platform.system()
    if system == "Windows":
        subprocess.run(["explorer", "/select,", path])
    elif system == "Darwin":
        subprocess.run(["open", "-R", path])
    else:
        subprocess.run(["xdg-open", str(Path(path).parent)])
