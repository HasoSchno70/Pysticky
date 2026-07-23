# -*- coding: utf-8 -*-
"""
Runde 49 (Layer-Umsortierung): gezielte Grenzfall-Untersuchung von
`LayerStack.move_layer`/`move_layer_to` und der Drag&Drop-Verdrahtung im
`LayerPanel` (Display-Index <-> tatsaechlicher Stack-Index).

Kein echter Bug gefunden -- diese Tests haerten das bereits korrekte
Verhalten ab, das im Zuge der Untersuchung mit echt ausgefuehrtem Code
verifiziert wurde:

1. Der aktive Layer bleibt nach einer Umsortierung per Objekt-Identitaet
   korrekt als aktiv markiert (`active_index` folgt der Verschiebung),
   unabhaengig davon ob der aktive Layer selbst verschoben wird oder ein
   anderer Layer an ihm vorbeigeschoben wird.
2. Verschieben an die obere/untere Grenze (oder bei nur einem einzigen
   Layer) ist ein sauberes No-Op (`False`), kein IndexError.
3. Sichtbarkeit/Sperre haengen am Layer-Objekt, nicht an der Position --
   sie "kleben" korrekt an der richtigen Ebene, wenn sich deren Index
   durch eine Umsortierung aendert.
4. `LayerStack.get_composite_grid()` spiegelt die neue Stapelreihenfolge
   sofort wider (kein gecachtes/veraltetes Ergebnis auf Stack-Ebene).
5. `LayerPanel._on_layers_reordered()` (der tatsaechliche Drag&Drop-
   Handler) rechnet Display-Index korrekt in Stack-Index um und haelt
   die UI-Auswahl (`currentRow`) nach dem Rebuild auf dem aktiven Layer.
"""

import pytest

from pysticky.core.layer import LayerStack

pytestmark = pytest.mark.usefixtures("qtbot")


# ---------------------------------------------------------------------------
# LayerStack-Ebene: move_layer / move_layer_to
# ---------------------------------------------------------------------------


def test_move_layer_preserves_active_layer_identity_when_other_layer_moves():
    """Wird ein NICHT-aktiver Layer verschoben, muss der aktive Layer (per
    Objekt-Identitaet) aktiv bleiben, auch wenn sich sein Index dadurch
    verschiebt."""
    stack = LayerStack(5, 5)
    stack.add_layer("L1")
    stack.add_layer("L2")  # aktuell: 0=Hintergrund, 1=L1, 2=L2
    stack.active_index = 1  # L1 aktiv

    assert stack.move_layer_to(0, 2) is True  # Hintergrund ans obere Ende

    assert stack.active_layer is not None
    assert stack.active_layer.name == "L1"


def test_move_layer_preserves_active_layer_identity_when_active_layer_moves():
    """Wird der aktive Layer selbst verschoben, muss er danach weiterhin
    aktiv sein (nicht der Layer, der jetzt zufaellig seinen alten Index
    belegt)."""
    stack = LayerStack(5, 5)
    stack.add_layer("L1")
    stack.add_layer("L2")
    stack.active_index = 1  # L1 aktiv

    assert stack.move_layer_to(1, 0) is True  # L1 ganz nach unten

    assert stack.active_layer is not None
    assert stack.active_layer.name == "L1"
    assert stack.active_index == 0


@pytest.mark.parametrize(
    "method,index",
    [("move_layer_up", 2), ("move_layer_down", 0)],
)
def test_move_layer_at_boundary_is_clean_noop(method, index):
    """Obersten Layer weiter nach oben / untersten weiter nach unten
    verschieben: sauberes False, keine Veraenderung der Reihenfolge."""
    stack = LayerStack(5, 5)
    stack.add_layer("L1")
    stack.add_layer("L2")
    names_before = [layer.name for layer in stack.layers]

    result = getattr(stack, method)(index)

    assert result is False
    assert [layer.name for layer in stack.layers] == names_before


def test_move_layer_single_layer_stack_does_not_crash():
    """Nur ein Layer im Pattern: Rauf/Runter-Versuch muss ein sauberes
    No-Op sein, kein IndexError/Crash."""
    stack = LayerStack(5, 5)
    assert len(stack) == 1

    assert stack.move_layer_up(0) is False
    assert stack.move_layer_down(0) is False
    assert stack.move_layer(0, 0) is True
    assert len(stack) == 1


def test_visibility_and_lock_stick_to_layer_object_across_move():
    """Sichtbarkeit/Sperre sind Eigenschaften des Layer-OBJEKTS -- sie
    duerfen nach move_layer_to() nicht an der alten Indexposition
    'kleben bleiben', sondern muessen mit dem Layer wandern."""
    stack = LayerStack(5, 5)
    stack.add_layer("L1")
    stack.add_layer("L2")
    stack[0].visible = False  # Hintergrund versteckt
    stack[1].locked = True  # L1 gesperrt

    stack.move_layer_to(0, 2)  # Hintergrund (versteckt) ganz nach oben

    hintergrund = next(layer for layer in stack.layers if layer.name == "Hintergrund")
    l1 = next(layer for layer in stack.layers if layer.name == "L1")
    assert hintergrund.visible is False
    assert l1.locked is True


def test_composite_grid_reflects_new_stacking_order_after_move():
    """get_composite_grid() darf nach einer Umsortierung kein veraltetes
    Ergebnis liefern -- der jetzt oberste sichtbare Layer muss gewinnen."""
    stack = LayerStack(3, 3)
    stack.add_layer("Top")  # 0=Hintergrund, 1=Top
    stack[0].set_stitch(0, 0, 5)
    stack[1].set_stitch(0, 0, 9)

    assert stack.get_composite_grid()[0, 0] == 9  # Top gewinnt zuerst

    stack.move_layer_to(0, 1)  # Hintergrund wird zum neuen obersten Layer

    assert stack.get_composite_grid()[0, 0] == 5  # jetzt gewinnt Hintergrund


# ---------------------------------------------------------------------------
# LayerPanel-Ebene: Display-Index <-> Stack-Index bei Drag&Drop
# ---------------------------------------------------------------------------


def test_panel_reorder_keeps_active_layer_selected_in_ui(qtbot):
    """`_on_layers_reordered` (der reale Drag&Drop-Handler) muss nach dem
    Verschieben eines FREMDEN Layers den aktiven Layer weiterhin korrekt
    in der Liste markiert lassen (currentRow folgt dem Display-Index der
    aktiven Ebene, nicht der alten Position)."""
    from pysticky.ui.panels.layer_panel import LayerPanel

    stack = LayerStack(5, 5)
    stack.add_layer("L1")
    stack.add_layer("L2")  # aktuell: 0=Hintergrund, 1=L1, 2=L2(oben)
    stack.active_index = 1  # L1 aktiv

    panel = LayerPanel()
    qtbot.addWidget(panel)
    panel.set_layer_stack(stack)

    # Display: 0=L2(oben), 1=L1, 2=Hintergrund(unten)
    assert panel.list_widget.currentRow() == 1

    # Hintergrund (display 2) an die Spitze ziehen (display 0)
    panel._on_layers_reordered(2, 0)

    assert stack.active_layer is not None
    assert stack.active_layer.name == "L1"
    # Neue Reihenfolge (unten->oben): L1, L2, Hintergrund
    # -> Display (oben->unten): Hintergrund(0), L2(1), L1(2)
    assert panel.list_widget.currentRow() == 2


def test_panel_reorder_moving_active_layer_updates_selection(qtbot):
    """Wird der aktive Layer selbst per Drag&Drop verschoben, muss die
    UI-Auswahl ihm an die neue Position folgen."""
    from pysticky.ui.panels.layer_panel import LayerPanel

    stack = LayerStack(5, 5)
    stack.add_layer("L1")
    stack.add_layer("L2")
    stack.active_index = 1  # L1 aktiv, Display-Index 1

    panel = LayerPanel()
    qtbot.addWidget(panel)
    panel.set_layer_stack(stack)

    # L1 (display 1) an die Spitze ziehen (display 0)
    panel._on_layers_reordered(1, 0)

    assert stack.active_layer is not None
    assert stack.active_layer.name == "L1"
    assert panel.list_widget.currentRow() == 0


def test_panel_reorder_clears_undo_history(qtbot):
    """Eine Umsortierung aendert Layer-Indizes -- bereits ausgefuehrte
    Undo-Commands (fester `layer_index`) wuerden sonst auf die falsche
    Ebene zeigen. `layer_structure_changed` muss auch beim echten
    Drag&Drop-Pfad (nicht nur beim manuellen Signal-Emit) feuern."""
    from pysticky.ui.panels.layer_panel import LayerPanel

    stack = LayerStack(5, 5)
    stack.add_layer("L1")

    panel = LayerPanel()
    qtbot.addWidget(panel)
    panel.set_layer_stack(stack)

    received: list[str] = []
    panel.layer_structure_changed.connect(lambda: received.append("structure"))
    panel.layers_changed.connect(lambda: received.append("changed"))

    panel._on_layers_reordered(1, 0)

    assert "structure" in received
    assert "changed" in received
