# -*- coding: utf-8 -*-
"""
Runde 67 - Audit der mypy-Verdachtsmomente in ui/widgets/tool_bar.py.

mypy (638-Fehler-Baseline) listet mehrere Typ-Warnungen rund um
Signal-Verdrahtung und die ActionButton/ToolButton-Klassenhierarchie:
- `_add_action()`: Parameter `signal: Signal` bekommt tatsaechlich immer
  eine gebundene `SignalInstance` (z.B. `self.mirror_h_clicked`) uebergeben
  -- "incompatible type" beim Aufruf UND bei `signal.emit` im Rumpf.
- `reapply_styles()`: die Schleifenvariable `btn` wird nacheinander ueber
  `_buttons.values()` (ToolButton), `_toggle_buttons` (ToggleToolButton)
  und `_action_buttons` (ActionButton) iteriert -- mypy reklamiert das als
  inkompatible Neuzuweisung.

Ergebnis dieser Audit-Runde: KEIN echter Laufzeitbug. Alle drei Stellen
sind reine Typannotations-Unschaerfe (PySide6-Stubs unterscheiden `Signal`
als Klassenattribut von `SignalInstance` als gebundene Instanz; mypy kann
das bei einer als `Signal` getippten Parametersignatur nicht auflösen,
und narrt die Schleifenvariable strikt nach dem erstbenutzten Typ). Zur
Laufzeit funktionieren `signal.emit()`, `btn._apply_stylesheet()` (auf
allen drei Sammlungen) und die komplette Klick-/Toggle-/Shortcut-Kette
nachweislich korrekt (siehe Tests unten).

Methodischer Fallstrick beim Testen von Tastenkuerzeln auf einem
QAbstractButton (im Unterschied zu einer QAction, siehe
test_shortcut_focus_scope.py): `setShortcut()` auf einem Button loest bei
Aktivierung intern `animateClick()` aus, das den Klick per Timer um die
QAbstractButton-Standardverzoegerung (100ms) NACH dem Tastendruck
ausfuehrt -- ein `qtbot.wait()` mit zu kurzer Dauer nach dem simulierten
Tastendruck taeuscht faelschlich ein "Shortcut wirkungslos" vor.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow

from pysticky.ui.tools.tool_enum import Tool
from pysticky.ui.widgets.tool_bar import ActionButton, ToolBar, ToolButton


def test_mirror_action_buttons_emit_signal_on_click(qtbot):
    """Verdachtsmoment 1 (mypy ~Z.470/472/639): _add_action() verbindet
    btn.clicked mit signal.emit, wobei `signal` als `Signal`
    (Klassenattribut) getippt ist, tatsaechlich aber immer eine gebundene
    SignalInstance uebergeben wird. emit() funktioniert zur Laufzeit
    trotzdem einwandfrei -- reines Typannotations-Problem."""
    bar = ToolBar()
    qtbot.addWidget(bar)

    received_h = []
    received_v = []
    bar.mirror_h_clicked.connect(lambda: received_h.append(True))
    bar.mirror_v_clicked.connect(lambda: received_v.append(True))

    mirror_h_btn = bar._action_buttons[0]
    mirror_v_btn = bar._action_buttons[1]
    assert isinstance(mirror_h_btn, ActionButton)
    assert isinstance(mirror_v_btn, ActionButton)

    qtbot.mouseClick(mirror_h_btn, Qt.MouseButton.LeftButton)
    assert received_h == [True]
    assert received_v == []

    qtbot.mouseClick(mirror_v_btn, Qt.MouseButton.LeftButton)
    assert received_v == [True]


def test_action_buttons_apply_stylesheet_without_attribute_error(qtbot):
    """Verdachtsmoment 2 (mypy ~Z.557): reapply_styles() iteriert ueber
    _buttons.values() (ToolButton), _toggle_buttons (ToggleToolButton) und
    _action_buttons (ActionButton) und ruft jeweils btn._apply_stylesheet()
    auf -- mypy reklamiert die Wiederverwendung der Schleifenvariable `btn`
    mit inkompatiblen Typen. Der Aufruf klappt zur Laufzeit fuer ALLE drei
    Typen ohne AttributeError, da jede Klasse ihre eigene
    _apply_stylesheet()-Methode besitzt."""
    bar = ToolBar()
    qtbot.addWidget(bar)

    # Sollte nicht crashen -- ruft _apply_stylesheet() auf allen drei
    # Button-Sammlungen auf (ToolButton, ToggleToolButton, ActionButton).
    bar.reapply_styles()

    for btn in bar._action_buttons:
        assert isinstance(btn, ActionButton)
        btn._apply_stylesheet()


def test_tool_click_emits_tool_changed_with_correct_tool(qtbot):
    """Klick auf einen Toolbar-Button loest tool_changed mit dem richtigen
    Tool-Identifier aus."""
    bar = ToolBar()
    qtbot.addWidget(bar)

    received = []
    bar.tool_changed.connect(lambda tool: received.append(tool))

    fill_btn = bar._buttons[Tool.FILL]
    qtbot.mouseClick(fill_btn, Qt.MouseButton.LeftButton)

    assert received == [Tool.FILL]
    assert bar.current_tool == Tool.FILL


def test_only_one_button_checked_at_a_time(qtbot):
    """Beim Wechsel zwischen Werkzeugen bleibt immer genau EIN Button aktiv
    (QButtonGroup exclusive)."""
    bar = ToolBar()
    qtbot.addWidget(bar)

    def checked_count():
        return sum(1 for btn in set(bar._buttons.values()) if btn.isChecked())

    assert checked_count() == 1  # PENCIL initial

    qtbot.mouseClick(bar._buttons[Tool.FILL], Qt.MouseButton.LeftButton)
    assert checked_count() == 1

    qtbot.mouseClick(bar._buttons[Tool.ERASER], Qt.MouseButton.LeftButton)
    assert checked_count() == 1


def test_shortcut_triggers_same_signal_as_click(qtbot):
    """Tastenkuerzel (hier 'P' fuer Stift) loest dasselbe Signal aus wie
    ein Mausklick und aktualisiert den Checked-Zustand -- muss in einem
    ECHTEN aktiven Fenster getestet werden (WindowShortcut-Kontext), und
    `animateClick()`s ~100ms-Verzoegerung muss abgewartet werden, sonst
    taeuscht ein zu kurzer `qtbot.wait()` ein "wirkungslos" vor."""
    win = QMainWindow()
    bar = ToolBar(win)
    win.setCentralWidget(bar)
    qtbot.addWidget(win)

    win.show()
    win.activateWindow()
    win.raise_()
    with qtbot.waitExposed(win):
        pass
    with qtbot.waitActive(win):
        pass

    # Erst zu einem anderen Tool wechseln, damit der Shortcut sichtbar
    # etwas aendert.
    eraser_btn = bar._buttons[Tool.ERASER]
    qtbot.mouseClick(eraser_btn, Qt.MouseButton.LeftButton)
    assert bar.current_tool == Tool.ERASER

    received = []
    bar.tool_changed.connect(lambda tool: received.append(tool))

    pencil_btn = bar._buttons[Tool.PENCIL]
    assert isinstance(pencil_btn, ToolButton)
    # Shortcut fuer Stift ist "P" (siehe _add_tool-Aufruf in _setup_ui).
    eraser_btn.setFocus(Qt.FocusReason.OtherFocusReason)
    qtbot.wait(10)
    qtbot.keyClick(eraser_btn, Qt.Key.Key_P)
    qtbot.wait(200)  # animateClick()-Standardverzoegerung abwarten

    assert bar.current_tool == Tool.PENCIL
    assert pencil_btn.isChecked() is True
    assert received == [Tool.PENCIL]
