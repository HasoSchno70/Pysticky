# -*- coding: utf-8 -*-
"""
Pytest Konfiguration und Fixtures.
"""

import sys
from pathlib import Path

import pytest

# Projekt-Root zum Path hinzufügen
project_root = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session", autouse=True)
def _isolate_qsettings_from_real_registry(tmp_path_factory):
    """Verhindert, dass Tests via echter QSettings(ORG_NAME, APP_NAME)-Kon-
    struktion (z.B. ueber ein echtes MainWindow()) in die tatsaechliche
    Windows-Registry des Nutzers unter HKCU\\Software\\PySticky schreiben.

    MainWindow._settings = QSettings(ORG_NAME, APP_NAME) gibt kein Format an.
    QSettings.setDefaultFormat() allein reicht NICHT aus -- der explizite
    2-Arg-Konstruktor QSettings(organization, application) ignoriert
    defaultFormat() nachweislich (per Repro-Skript verifiziert: liefert
    weiterhin format()==NativeFormat / fileName()=="\\HKEY_CURRENT_USER\\...")
    und schreibt also trotzdem in die echte Registry. Ohne einen Fix landen
    Testartefakte (z.B. pytest-tmp-Pfade in "recent_files") direkt in der
    echten Registry des Nutzers -- reproduzierbar beobachtet: ein Suite-Lauf
    nach Runde 49 hat vier pytest-tmp-Pfade in den echten recent_files-Wert
    geschrieben.

    Fix: QSettings.__init__ selbst wird gepatcht, sodass JEDE Konstruktion
    mit (organization[, application])-Signatur zwingend auf IniFormat +
    UserScope + ein Session-Temp-Verzeichnis umgeleitet wird -- unabhaengig
    davon, welches Modul QSettings importiert hat (die Klasse ist ein
    einziges gemeinsames Objekt, das Patchen wirkt also global). Der
    parameterlose Konstruktor QSettings() nutzt weiterhin defaultFormat()
    (hier ebenfalls auf IniFormat gesetzt), fuer den Fall, dass ein Test
    QCoreApplication.setOrganizationName()/setApplicationName() nutzt.
    """
    from PySide6.QtCore import QSettings

    settings_dir = tmp_path_factory.mktemp("qsettings_isolated")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(settings_dir))
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.SystemScope, str(settings_dir))

    orig_init = QSettings.__init__

    def _isolated_init(self, *args, **kwargs):
        if args and isinstance(args[0], str) and not kwargs:
            organization = args[0]
            application = args[1] if len(args) >= 2 else ""
            orig_init(
                self,
                QSettings.Format.IniFormat,
                QSettings.Scope.UserScope,
                organization,
                application,
            )
        else:
            orig_init(self, *args, **kwargs)

    QSettings.__init__ = _isolated_init
    yield
    QSettings.__init__ = orig_init


@pytest.fixture(autouse=True)
def _no_autosave_side_effects(monkeypatch):
    """Neutralisiert Autosave-Interaktion in ALLEN Tests.

    1. _check_autosave_recovery öffnet einen echten modalen QMessageBox.question,
       wenn %TEMP%/pysticky_autosave.pxs (Start) oder <datei>.pxs.autosave
       (nach _load_pattern_file) existiert — hängt die Suite für immer.
    2. _on_autosave schreibt bei Patterns ohne current_file genau diese Datei
       nach %TEMP% — Autosave-Timer von Test-MainWindows können während langer
       Tests (oder Hängern) feuern und so die Falle für den NÄCHSTEN Lauf legen.
    Kein Test testet Recovery interaktiv; wer Autosave testen will, ruft
    _on_autosave gezielt mit gesetztem current_file auf (siehe
    test_save_error_handling.py).
    """
    try:
        from pysticky.ui.handlers.autosave_handlers import AutosaveHandlersMixin
    except ImportError:
        yield
        return

    monkeypatch.setattr(
        AutosaveHandlersMixin, "_check_autosave_recovery", lambda self, autosave_path=None: None
    )
    yield


@pytest.fixture
def empty_pattern():
    """Leeres 10x10 Muster."""
    from pysticky.core import Pattern

    return Pattern(name="Test", width=10, height=10)


@pytest.fixture
def pattern_with_colors():
    """Muster mit 5 Farben."""
    from pysticky.core import Pattern, Thread

    pattern = Pattern(name="Farbtest", width=20, height=20)
    pattern.color_entries.clear()

    colors = [
        ("Schwarz", "#000000", "310"),
        ("Weiß", "#FFFFFF", "B5200"),
        ("Rot", "#FF0000", "321"),
        ("Grün", "#00FF00", "699"),
        ("Blau", "#0000FF", "796"),
    ]

    for name, hex_color, num in colors:
        thread = Thread.from_hex(name, hex_color, manufacturer="DMC", catalog_number=num)
        pattern.add_color(thread)

    return pattern


@pytest.fixture
def pattern_with_stitches(pattern_with_colors):
    """Muster mit einigen Stichen."""
    pattern = pattern_with_colors

    # Rechteck zeichnen
    for x in range(5, 15):
        pattern.set_stitch(x, 5, 0)  # Oben
        pattern.set_stitch(x, 14, 0)  # Unten
    for y in range(5, 15):
        pattern.set_stitch(5, y, 0)  # Links
        pattern.set_stitch(14, y, 0)  # Rechts

    # Füllung
    for y in range(6, 14):
        for x in range(6, 14):
            pattern.set_stitch(x, y, 2)  # Rot

    return pattern


@pytest.fixture
def undo_manager():
    """UndoManager Instanz."""
    from pysticky.core import UndoManager

    return UndoManager(max_history=50)


@pytest.fixture
def temp_pattern_file(tmp_path):
    """Temporärer Pfad für Pattern-Datei."""
    return tmp_path / "test_pattern.pxs"
