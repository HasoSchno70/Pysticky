# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 29): LayerPanel._on_rename_layer() aenderte
layer.name und rief _refresh_list() auf, emittierte aber -- anders als
alle anderen Layer-Panel-Operationen (Deckkraft, Notiz, Sichtbarkeit,
Struktur-Aenderungen) -- KEIN `layers_changed`-Signal.

MainWindow._on_layers_changed() ist der einzige Ort, der
`self._mark_unsaved()` fuer Layer-Panel-Aenderungen aufruft (siehe
src/pysticky/ui/handlers/panel_handlers.py). Ohne das Signal blieb
`_unsaved_changes` nach einer reinen Umbenennung auf False -- ein Nutzer,
der eine Ebene umbenennt und die App dann schliesst (ohne eine weitere,
"zaehlende" Aenderung vorzunehmen), bekam keine "Ungespeicherte
Aenderungen?"-Abfrage und verlor die neue Bezeichnung beim naechsten
Laden der .pxs-Datei stillschweigend.
"""

import pytest

from pysticky.core.layer import LayerStack

pytestmark = pytest.mark.usefixtures("qtbot")


def test_rename_layer_emits_layers_changed(qtbot, monkeypatch):
    from PySide6.QtWidgets import QInputDialog

    from pysticky.ui.panels.layer_panel import LayerPanel

    panel = LayerPanel()
    qtbot.addWidget(panel)

    stack = LayerStack(10, 10)
    panel.set_layer_stack(stack)

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Neuer Name", True)))

    received = []
    panel.layers_changed.connect(lambda: received.append(True))

    panel.list_widget.setCurrentRow(0)
    panel._on_rename_layer()

    assert stack[0].name == "Neuer Name"
    assert received == [True], (
        "layers_changed muss auch bei einer reinen Umbenennung feuern, "
        "sonst wird die Aenderung nie als 'unsaved' markiert (MainWindow "
        "._on_layers_changed -> _mark_unsaved)."
    )


def test_rename_layer_declined_emits_nothing(qtbot, monkeypatch):
    from PySide6.QtWidgets import QInputDialog

    from pysticky.ui.panels.layer_panel import LayerPanel

    panel = LayerPanel()
    qtbot.addWidget(panel)

    stack = LayerStack(10, 10)
    panel.set_layer_stack(stack)

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("", False)))

    received = []
    panel.layers_changed.connect(lambda: received.append(True))

    panel.list_widget.setCurrentRow(0)
    panel._on_rename_layer()

    assert received == []
