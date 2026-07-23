# -*- coding: utf-8 -*-
"""
Audit-Runde: Tastenkuerzel-Kontext-Leckage.

Fragestellung: Loesen die global registrierten QActions fuer
Canvas-Operationen (Kopieren/Ausschneiden/Einfuegen/Loeschen/Rueckgaengig
-- Ctrl+C/X/V/Entf/Ctrl+Z, siehe mw_actions_mixin.py) faelschlich aus,
waehrend der Tastaturfokus tatsaechlich in einem Text-Eingabefeld
(QLineEdit/QPlainTextEdit) liegt, das direkt im MainWindow-Fenster gedockt
ist (Paletten-Suchfeld, Ebenen-Notizfeld)? Das waere eine Kontext-
Leckage: der Nutzer will nur im Textfeld kopieren/loeschen/rueckgaengig
machen, aber der Canvas-Handler feuert (zusaetzlich oder stattdessen).

Ergebnis dieser Audit-Runde: KEIN Bug gefunden.
- Kein setShortcutContext()-Aufruf irgendwo im Code (grep bestaetigt) --
  alle Canvas-Shortcuts laufen auf Qt's Default-Kontext (WindowShortcut).
- Kein Tastatur-bezogener Event-Filter (die vorhandenen eventFilter()-
  Implementierungen betreffen nur Mausrad/Scroll/Tooltip, nicht
  Tastatur-Events -- wheel_guard.py, color_bar.py, canvas_container.py,
  custom_tooltip.py).
- MainWindow.keyPressEvent behandelt nur die '?'-Taste manuell, alles
  andere geht per super() an Qt's Standardrouting.
- QLineEdit/QPlainTextEdit akzeptieren den QEvent::ShortcutOverride fuer
  Standard-Editier-Sequenzen (Copy/Cut/Paste/Undo/Delete) bedingungslos
  bei Fokus -- nicht nur wenn lokal tatsaechlich etwas zu tun waere.
  Selbst ein frisches Feld ohne Undo-Historie oder ohne aktuelle
  Selektion blockt die globale Aktion lokal (empirisch mit einer
  Kontrollprobe verifiziert, siehe test_probe_confirms_harness_can_
  detect_a_real_leak unten).

Methodischer Fallstrick, der hier eine erste (falsche) "alles sauber"-
Messung erzeugt haette: QTest.keyClick()/qtbot.keyClick() lösen den
Qt-Shortcut-Mechanismus nur aus, wenn das Fenster tatsaechlich als
"aktiv" gilt (QMainWindow.isActiveWindow()). Ohne vorheriges
show()+activateWindow()+raise_()+waitActive() feuert GAR KEINE QAction,
auch nicht bei einem simplen QPushButton als Fokus-Ziel -- das haette
jeden Befund hier als falsches "clean" maskiert. Der Positivkontroll-Test
unten stellt sicher, dass der Test-Aufbau den Mechanismus tatsaechlich
scharf schaltet, bevor die eigentlichen Negativ-Befunde als aussagekraeftig
gelten.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QTextCursor
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture
def main_window(qtbot):
    if QApplication.instance() is None:
        QApplication([])

    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    w.show()
    w.activateWindow()
    w.raise_()
    qtbot.waitExposed(w)
    qtbot.waitActive(w)
    return w


def test_probe_confirms_harness_can_detect_a_real_leak(qtbot):
    """Positivkontrolle: bevor wir 'kein Leck' als Ergebnis werten, muss
    der Testaufbau selbst beweisen, dass er ein Leck ueberhaupt erkennen
    KOENNTE. Ein Fokus-Ziel ohne eigene Copy-Behandlung (ein simples
    QMainWindow ohne Text-Widget) MUSS die globale Ctrl+C-QAction
    ausloesen -- sonst waere jeder 'sauber'-Befund unten wertlos, weil
    QTest.keyClick() den Shortcut-Mechanismus gar nicht scharf schaltet."""
    win = QMainWindow()
    qtbot.addWidget(win)
    button = QPushButton("focus target, no own Ctrl+C handling")
    win.setCentralWidget(button)
    calls = []
    action = QAction("Copy", win)
    action.setShortcut(QKeySequence.StandardKey.Copy)
    action.triggered.connect(lambda: calls.append(1))
    win.addAction(action)
    win.show()
    win.activateWindow()
    win.raise_()
    qtbot.waitExposed(win)
    qtbot.waitActive(win)
    button.setFocus(Qt.FocusReason.OtherFocusReason)
    qtbot.wait(10)
    assert QApplication.focusWidget() is button

    qtbot.keyClick(button, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)

    assert calls == [1], (
        "Testaufbau schaltet den Qt-Shortcut-Mechanismus nicht scharf -- "
        "ohne diese Kontrolle waeren alle folgenden 'kein Leck'-Befunde "
        "nicht aussagekraeftig."
    )


def test_palette_search_copy_with_selection_stays_local(main_window, qtbot):
    """Ctrl+C im fokussierten Paletten-Suchfeld (QLineEdit, direkt im
    MainWindow gedockt) darf NICHT zusaetzlich action_selection_copy
    (Canvas-Kopieren) ausloesen -- nur das Textfeld soll seine eigene
    Selektion ins Clipboard kopieren."""
    w = main_window
    edit = w.palette_panel.edit_search

    copy_calls = []
    w.action_selection_copy.triggered.connect(lambda: copy_calls.append(1))

    edit.setText("dmc rot")
    edit.setFocus(Qt.FocusReason.OtherFocusReason)
    qtbot.wait(10)
    assert QApplication.focusWidget() is edit
    edit.selectAll()

    qtbot.keyClick(edit, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    qtbot.wait(10)

    assert copy_calls == []
    assert QApplication.clipboard().text() == "dmc rot"


def test_palette_search_delete_key_stays_local(main_window, qtbot):
    """Entf-Taste im fokussierten Suchfeld darf nicht
    action_selection_delete (Stiche in Canvas-Auswahl loeschen) ausloesen
    -- nur ein Zeichen im Textfeld soll geloescht werden."""
    w = main_window
    edit = w.palette_panel.edit_search

    delete_calls = []
    w.action_selection_delete.triggered.connect(lambda: delete_calls.append(1))

    edit.setText("hello")
    edit.setCursorPosition(0)
    edit.setFocus(Qt.FocusReason.OtherFocusReason)
    qtbot.wait(10)

    qtbot.keyClick(edit, Qt.Key.Key_Delete)
    qtbot.wait(10)

    assert delete_calls == []
    assert edit.text() == "ello"


def test_layer_note_undo_after_typing_stays_local(main_window, qtbot):
    """Hoechster Risiko-Fall: Nutzer tippt in der Ebenen-Notiz (QPlainTextEdit,
    direkt im MainWindow gedockt), hat aber VOR dem Tippen bereits eine
    rueckgaengig-machbare Canvas-Aktion ausgefuehrt (action_undo daher
    aktiv). Ctrl+Z soll trotzdem nur den zuletzt getippten Text lokal
    zuruecknehmen -- nicht den letzten Canvas-Undo-Schritt (der sonst
    unbemerkt Stiche entfernen wuerde)."""
    w = main_window
    note = w.layer_panel.edit_note

    undo_calls = []
    w.action_undo.triggered.connect(lambda: undo_calls.append(1))
    # Worst Case nachstellen: Canvas hat tatsaechlich etwas rueckgaengig
    # zu machen, die Aktion ist also aktiv -- nicht wie im Normalfall
    # deaktiviert.
    w.action_undo.setEnabled(True)

    note.setPlainText("Vordergrund")
    note.moveCursor(QTextCursor.MoveOperation.End)
    note.setFocus(Qt.FocusReason.OtherFocusReason)
    qtbot.wait(10)
    assert QApplication.focusWidget() is note
    qtbot.keyClicks(note, " layer")
    assert note.toPlainText() == "Vordergrund layer"
    assert note.document().isUndoAvailable()

    qtbot.keyClick(note, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    qtbot.wait(10)

    assert undo_calls == []
    # Die lokale Texteingabe wurde zurueckgenommen, nicht ein Canvas-Schritt.
    assert note.toPlainText() == "Vordergrund"


def test_layer_note_delete_key_stays_local(main_window, qtbot):
    """Entf-Taste in der Ebenen-Notiz (anderer Widget-Typ als QLineEdit)
    darf ebenfalls nicht action_selection_delete ausloesen."""
    w = main_window
    note = w.layer_panel.edit_note

    delete_calls = []
    w.action_selection_delete.triggered.connect(lambda: delete_calls.append(1))

    note.setPlainText("Notiztext")
    cursor = note.textCursor()
    cursor.setPosition(0)
    note.setTextCursor(cursor)
    note.setFocus(Qt.FocusReason.OtherFocusReason)
    qtbot.wait(10)

    qtbot.keyClick(note, Qt.Key.Key_Delete)
    qtbot.wait(10)

    assert delete_calls == []
    assert note.toPlainText() == "otiztext"


def test_palette_search_paste_and_cut_stay_local(main_window, qtbot):
    """Ctrl+V/Ctrl+X im Suchfeld duerfen nicht action_selection_paste bzw.
    action_selection_cut (Canvas-Einfuegen/-Ausschneiden) ausloesen."""
    w = main_window
    edit = w.palette_panel.edit_search

    paste_calls = []
    w.action_selection_paste.triggered.connect(lambda: paste_calls.append(1))
    cut_calls = []
    w.action_selection_cut.triggered.connect(lambda: cut_calls.append(1))

    QApplication.clipboard().setText("clipdata")
    edit.clear()
    edit.setFocus(Qt.FocusReason.OtherFocusReason)
    qtbot.wait(10)
    qtbot.keyClick(edit, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
    qtbot.wait(10)

    assert paste_calls == []
    assert edit.text() == "clipdata"

    edit.selectAll()
    qtbot.keyClick(edit, Qt.Key.Key_X, Qt.KeyboardModifier.ControlModifier)
    qtbot.wait(10)

    assert cut_calls == []
    assert edit.text() == ""
    assert QApplication.clipboard().text() == "clipdata"
