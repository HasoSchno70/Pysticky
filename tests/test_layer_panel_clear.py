# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 16): LayerPanel._on_clear_layer() rief
layer.clear() DIREKT auf -- komplett am Undo-System vorbei (nicht
undoable via Strg+Z), ohne layer.locked zu respektieren, und ohne
color_entries[i].stitch_count zu aktualisieren (das Panel kennt nur den
LayerStack, nicht das volle Pattern, das fuer die Stichzahl-Buchfuehrung
noetig ist). ClearLayerCommand existierte fuer genau diesen Zweck, wurde
aber nirgendwo im Programm tatsaechlich konstruiert. Jetzt emittiert das
Panel ein Signal, das MainWindow in einen echten ClearLayerCommand
uebersetzt (siehe test_clear_layer_requested_handler.py fuer den
MainWindow-seitigen Teil).
"""

import pytest
from PySide6.QtWidgets import QMessageBox

from pysticky.core.layer import LayerStack

pytestmark = pytest.mark.usefixtures("qtbot")


def test_clear_layer_emits_signal_instead_of_calling_layer_clear_directly(qtbot, monkeypatch):
    from pysticky.ui.panels.layer_panel import LayerPanel

    panel = LayerPanel()
    qtbot.addWidget(panel)

    stack = LayerStack(10, 10)
    stack.active_layer.set_stitch(3, 3, 0)
    panel.set_layer_stack(stack)

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)

    received = []
    panel.clear_layer_requested.connect(lambda idx: received.append(idx))

    panel.list_widget.setCurrentRow(0)
    panel._on_clear_layer()

    assert received == [0]
    # Das Panel selbst darf das Grid NICHT veraendert haben -- das passiert
    # erst, wenn MainWindow den ClearLayerCommand tatsaechlich ausfuehrt.
    assert stack.active_layer.get_stitch(3, 3) == 0


def test_clear_layer_does_nothing_when_declined(qtbot, monkeypatch):
    from pysticky.ui.panels.layer_panel import LayerPanel

    panel = LayerPanel()
    qtbot.addWidget(panel)

    stack = LayerStack(10, 10)
    panel.set_layer_stack(stack)

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)

    received = []
    panel.clear_layer_requested.connect(lambda idx: received.append(idx))

    panel.list_widget.setCurrentRow(0)
    panel._on_clear_layer()

    assert received == []
