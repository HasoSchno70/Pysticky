# -*- coding: utf-8 -*-
"""
Regressionstests (Runde 56): systematischer Audit aller Command-Klassen in
core/undo.py auf dieselbe Luecke, die in Runde 55 bei PlaceStitchCommand
gefunden wurde ("Bead-/Diamond-Farben werden immer als BEAD-/DIAMOND-
Stitch-Type platziert" -- diese Regel lebt in Pattern.set_stitch(), Commands
die stattdessen direkt layer.set_stitch() mit einem beliebigen layer_index
aufrufen, muessen sie manuell duplizieren).

Ergebnis des Audits: KEINE weitere betroffene Klasse gefunden.
    - PlaceStitchCommand: bereits in Runde 55 gefixt (siehe test_gradient_
      tool_edge_cases.py::test_gradient_between_diamond_colors_keeps_
      diamond_stitch_type).
    - RemoveStitchCommand.undo(): restauriert einen zuvor per get_stitch_type()
      VOR dem Entfernen eingefangenen Stich-Typ -- keine neue "Platzierungs-
      Entscheidung" mit stitch_type=0-Default, sondern reines Zuruecklegen
      von bereits korrekt gestempelten Daten.
    - ClearLayerCommand.undo(): restauriert eine volle Grid-Kopie (inkl.
      stitch_type_grid) -- ebenfalls reines Zuruecklegen, keine Neu-
      Platzierung.
    - BatchStitchCommand: reiner Container, delegiert execute()/undo() an
      seine Sub-Commands (in der Praxis ausschliesslich PlaceStitchCommand/
      RemoveStitchCommand) -- profitiert automatisch vom Runde-55-Fix.
    - LayerSnapshotCommand: die `action`-Callback ruft laut Docstring und
      allen aktuellen Aufrufern (Plugin-Dialog, Farbverlauf-Batch) entweder
      `pattern.set_stitch()` (das die Regel selbst schon durchsetzt) oder
      Canvas-Methoden auf, die ihrerseits bereits korrekt gestempelte Stich-
      Typen 1:1 uebernehmen (mirror_selection_horizontal/vertical() kopiert
      einen zuvor per get_stitch_type() eingelesenen Typ weiter, keine neue
      stitch_type=0-Platzierung).
    - AddBackstitchCommand/RemoveBackstitchCommand: Rueckstiche haben kein
      BEAD/DIAMOND-Konzept (eigenes Backstitch-Datenmodell ohne Grid-
      Stich-Typ), daher nicht betroffen.
    - MarkStitchCompletedCommand/UnmarkStitchCompletedCommand/
      MarkColorCompletedCommand: aendern nur completion_grid, nie
      Farbe/Stich-Typ.

Diese Tests fixieren das bereits korrekte Verhalten der oben genannten
Klassen gegen zukuenftige Regressionen.
"""

from pysticky.core import (
    BatchStitchCommand,
    ClearLayerCommand,
    LayerSnapshotCommand,
    Pattern,
    PlaceStitchCommand,
    RemoveStitchCommand,
    Thread,
    UndoManager,
)
from pysticky.core.stitch import StitchType


def _diamond_pattern(width: int = 6, height: int = 6) -> Pattern:
    """Erstellt ein Pattern mit einer einzigen Diamond-Painting-Farbe (Index 0)."""
    pattern = Pattern(name="DP-Audit", width=width, height=height, mode="diamond")
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("DP-Rot", "#ff0000"), is_diamond=True)
    return pattern


class TestRemoveStitchCommandPreservesStitchType:
    """RemoveStitchCommand.undo() darf einen entfernten Diamond-Stich nicht
    als FULL(0) zurueckbringen."""

    def test_undo_restores_diamond_stitch_type(self):
        pattern = _diamond_pattern()
        layer_index = pattern.layer_stack.active_index

        place = PlaceStitchCommand(pattern, 2, 2, 0, layer_index)
        place.execute()
        assert pattern.active_layer.get_stitch_type(2, 2) == StitchType.DIAMOND.value

        remove = RemoveStitchCommand(pattern, 2, 2, layer_index)
        remove.execute()
        assert pattern.active_layer.get_stitch(2, 2) is None

        remove.undo()
        assert pattern.active_layer.get_stitch(2, 2) == 0
        assert pattern.active_layer.get_stitch_type(2, 2) == StitchType.DIAMOND.value, (
            "RemoveStitchCommand.undo() muss den DIAMOND-Stich-Typ wiederherstellen, "
            "nicht auf FULL zuruecksetzen"
        )


class TestClearLayerCommandPreservesStitchTypes:
    """ClearLayerCommand.undo() muss stitch_type_grid vollstaendig restaurieren,
    inklusive DIAMOND/BEAD-Zellen."""

    def test_undo_restores_diamond_stitch_types(self):
        pattern = _diamond_pattern()
        layer_index = pattern.layer_stack.active_index

        for x, y in [(0, 0), (1, 1), (2, 2)]:
            PlaceStitchCommand(pattern, x, y, 0, layer_index).execute()
        for x, y in [(0, 0), (1, 1), (2, 2)]:
            assert pattern.active_layer.get_stitch_type(x, y) == StitchType.DIAMOND.value

        clear = ClearLayerCommand(pattern, layer_index)
        clear.execute()
        assert pattern.active_layer.get_stitch(0, 0) is None

        clear.undo()
        for x, y in [(0, 0), (1, 1), (2, 2)]:
            assert pattern.active_layer.get_stitch(x, y) == 0
            assert pattern.active_layer.get_stitch_type(x, y) == StitchType.DIAMOND.value, (
                f"ClearLayerCommand.undo() muss DIAMOND-Typ bei ({x},{y}) wiederherstellen"
            )


class TestBatchStitchCommandDiamondEnforcement:
    """BatchStitchCommand delegiert nur an Sub-Commands -- mit
    PlaceStitchCommand-Subcommands auf einem NICHT-aktiven Layer (der Fall,
    fuer den PlaceStitchCommand in Runde 55 extra gefixt wurde) muss die
    Bead-/Diamond-Erzwingung trotzdem greifen."""

    def test_batch_of_place_commands_on_non_active_layer_enforces_diamond(self):
        pattern = _diamond_pattern()
        # Zweiten Layer anlegen, damit layer_index != active_index ist --
        # exakt das Szenario, fuer das PlaceStitchCommand layer.set_stitch()
        # statt pattern.set_stitch() verwenden muss.
        pattern.layer_stack.add_layer("Zweiter Layer")
        other_layer_index = 1
        # add_layer() macht den NEUEN Layer automatisch aktiv -- fuer dieses
        # Szenario muss layer_index gerade NICHT der aktive sein (das ist ja
        # der Grund, warum PlaceStitchCommand ueberhaupt layer.set_stitch()
        # statt pattern.set_stitch() aufruft), also Layer 0 wieder aktivieren.
        pattern.layer_stack.active_index = 0
        assert pattern.layer_stack.active_index != other_layer_index

        batch = BatchStitchCommand(pattern, "Diamond-Batch")
        batch.add_command(PlaceStitchCommand(pattern, 0, 0, 0, other_layer_index))
        batch.add_command(PlaceStitchCommand(pattern, 1, 0, 0, other_layer_index))
        batch.execute()

        target_layer = pattern.layer_stack[other_layer_index]
        assert target_layer.get_stitch_type(0, 0) == StitchType.DIAMOND.value
        assert target_layer.get_stitch_type(1, 0) == StitchType.DIAMOND.value

        batch.undo()
        assert target_layer.get_stitch(0, 0) is None
        assert target_layer.get_stitch(1, 0) is None


class TestLayerSnapshotCommandDiamondEnforcement:
    """LayerSnapshotCommand fuehrt eine beliebige Aktion aus und snapshot-ed
    davor/danach. Wenn diese Aktion (wie bei allen aktuellen Aufrufern)
    pattern.set_stitch() nutzt, muss die Diamond-Erzwingung greifen --
    sowohl beim ersten execute() als auch nach undo()/redo() (Redo
    restauriert nur den aufgezeichneten Nachher-Snapshot, ruft `action`
    nicht erneut auf)."""

    def test_execute_undo_redo_preserve_diamond_stitch_type(self):
        pattern = _diamond_pattern()
        layer_index = pattern.layer_stack.active_index

        def _place_via_pattern() -> None:
            pattern.set_stitch(3, 3, 0)

        undo_manager = UndoManager()
        undo_manager.set_pattern(pattern)

        cmd = LayerSnapshotCommand(
            pattern, layer_index=layer_index, action=_place_via_pattern, description_text="Test"
        )
        undo_manager.execute(cmd)
        assert pattern.active_layer.get_stitch(3, 3) == 0
        assert pattern.active_layer.get_stitch_type(3, 3) == StitchType.DIAMOND.value

        undo_manager.undo()
        assert pattern.active_layer.get_stitch(3, 3) is None

        undo_manager.redo()
        assert pattern.active_layer.get_stitch(3, 3) == 0
        assert pattern.active_layer.get_stitch_type(3, 3) == StitchType.DIAMOND.value, (
            "Redo muss den DIAMOND-Stich-Typ ueber den aufgezeichneten Nachher-Snapshot "
            "wiederherstellen"
        )
