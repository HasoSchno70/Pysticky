# -*- coding: utf-8 -*-
"""
Tests für das Undo-System.
"""

import pytest

from pysticky.core import (
    AddBackstitchCommand,
    BatchStitchCommand,
    LayerSnapshotCommand,
    Pattern,
    PlaceStitchCommand,
    RemoveBackstitchCommand,
    UndoManager,
)


class TestUndoManager:
    """Tests für UndoManager."""

    def test_initial_state(self):
        """Test: Initialer Zustand."""
        undo = UndoManager()

        assert undo.can_undo is False
        assert undo.can_redo is False
        assert undo.undo_count == 0
        assert undo.redo_count == 0

    def test_execute_adds_to_history(self):
        """Test: Execute fügt zur Historie hinzu."""
        pattern = Pattern(width=10, height=10)
        undo = UndoManager()
        undo.set_pattern(pattern)

        cmd = PlaceStitchCommand(pattern, 5, 5, 0, 0)
        undo.execute(cmd)

        assert undo.can_undo is True
        assert undo.undo_count == 1

    def test_undo_removes_from_history(self):
        """Test: Undo entfernt aus Historie."""
        pattern = Pattern(width=10, height=10)
        undo = UndoManager()
        undo.set_pattern(pattern)

        cmd = PlaceStitchCommand(pattern, 5, 5, 0, 0)
        undo.execute(cmd)
        undo.undo()

        assert undo.can_undo is False
        assert undo.can_redo is True

    def test_redo_restores(self):
        """Test: Redo stellt wieder her."""
        pattern = Pattern(width=10, height=10)
        undo = UndoManager()
        undo.set_pattern(pattern)

        cmd = PlaceStitchCommand(pattern, 5, 5, 0, 0)
        undo.execute(cmd)
        undo.undo()
        undo.redo()

        assert pattern.active_layer.get_stitch(5, 5) == 0

    def test_max_history(self):
        """Test: Historie wird begrenzt."""
        pattern = Pattern(width=10, height=10)
        undo = UndoManager(max_history=5)
        undo.set_pattern(pattern)

        for i in range(10):
            cmd = PlaceStitchCommand(pattern, i, 0, 0, 0)
            undo.execute(cmd)

        assert undo.undo_count == 5

    def test_clear(self):
        """Test: Historie leeren."""
        pattern = Pattern(width=10, height=10)
        undo = UndoManager()
        undo.set_pattern(pattern)

        cmd = PlaceStitchCommand(pattern, 5, 5, 0, 0)
        undo.execute(cmd)
        undo.clear()

        assert undo.can_undo is False
        assert undo.can_redo is False


class TestLockedLayerStitchCountGuard:
    """Regression (Runde 13): PlaceStitchCommand/RemoveStitchCommand
    dekrementierten/inkrementierten stitch_count bevor sie pruefte, ob
    layer.set_stitch()/remove_stitch() ueberhaupt etwas geaendert hat.
    Bei einem gesperrten Layer (set_stitch() gibt False zurueck, Grid
    unveraendert) driftete stitch_count trotzdem bei jedem Versuch."""

    def test_place_stitch_on_locked_layer_leaves_stitch_count_unchanged(self):
        pattern = Pattern(width=10, height=10)
        pattern.active_layer.set_stitch(5, 5, 0)
        pattern.color_entries[0].stitch_count = 1
        pattern.active_layer.locked = True

        cmd = PlaceStitchCommand(pattern, 5, 5, 0, 0)
        cmd.execute()

        assert pattern.active_layer.get_stitch(5, 5) == 0
        assert pattern.color_entries[0].stitch_count == 1

    def test_place_stitch_undo_on_locked_layer_is_noop(self):
        pattern = Pattern(width=10, height=10)
        undo = UndoManager()
        undo.set_pattern(pattern)

        cmd = PlaceStitchCommand(pattern, 5, 5, 0, 0)
        undo.execute(cmd)
        assert pattern.color_entries[0].stitch_count == 1

        # Layer erst NACH dem execute() sperren, damit undo() auf den
        # bereits ausgefuehrten Command trifft.
        pattern.active_layer.locked = True
        undo.undo()

        # set_stitch() im undo() schlaegt fehl (gesperrt) -- Grid und
        # Stichzahl duerfen dadurch NICHT veraendert werden.
        assert pattern.active_layer.get_stitch(5, 5) == 0
        assert pattern.color_entries[0].stitch_count == 1

    def test_remove_stitch_on_locked_layer_leaves_stitch_count_unchanged(self):
        from pysticky.core import RemoveStitchCommand

        pattern = Pattern(width=10, height=10)
        pattern.active_layer.set_stitch(5, 5, 0)
        pattern.color_entries[0].stitch_count = 1
        pattern.active_layer.locked = True

        cmd = RemoveStitchCommand(pattern, 5, 5, 0)
        cmd.execute()

        assert pattern.active_layer.get_stitch(5, 5) == 0
        assert pattern.color_entries[0].stitch_count == 1


class TestBatchCommand:
    """Tests für Batch-Operationen."""

    def test_batch_multiple_commands(self):
        """Test: Batch mit mehreren Commands."""
        pattern = Pattern(width=10, height=10)
        batch = BatchStitchCommand(pattern, "Test-Batch")

        batch.add_command(PlaceStitchCommand(pattern, 0, 0, 0, 0))
        batch.add_command(PlaceStitchCommand(pattern, 1, 1, 0, 0))
        batch.add_command(PlaceStitchCommand(pattern, 2, 2, 0, 0))

        batch.execute()

        assert pattern.active_layer.get_stitch(0, 0) == 0
        assert pattern.active_layer.get_stitch(1, 1) == 0
        assert pattern.active_layer.get_stitch(2, 2) == 0

    def test_batch_undo(self):
        """Test: Batch-Undo macht alle Änderungen rückgängig."""
        pattern = Pattern(width=10, height=10)
        batch = BatchStitchCommand(pattern, "Test-Batch")

        batch.add_command(PlaceStitchCommand(pattern, 0, 0, 0, 0))
        batch.add_command(PlaceStitchCommand(pattern, 1, 1, 0, 0))
        batch.execute()
        batch.undo()

        assert pattern.active_layer.get_stitch(0, 0) is None
        assert pattern.active_layer.get_stitch(1, 1) is None

    def test_batch_is_empty(self):
        """Test: Leerer Batch erkennen."""
        pattern = Pattern(width=10, height=10)
        batch = BatchStitchCommand(pattern, "Leer")

        assert batch.is_empty is True

        batch.add_command(PlaceStitchCommand(pattern, 0, 0, 0, 0))

        assert batch.is_empty is False

    def test_reentrant_begin_batch_commits_previous_batch_instead_of_losing_it(self):
        """Regression: ruft begin_batch() ein zweites Mal auf, WAEHREND eine
        vorige Batch noch offen ist (nie mit end_batch()/cancel_batch()
        beendet), ueberschrieb das frueher stillschweigend die Referenz auf
        die alte Batch -- deren bereits ausgefuehrte Sub-Commands (via
        add_to_batch()) verschwanden komplett aus der Undo-Historie, obwohl
        ihre Grid-Mutation laengst passiert war."""
        pattern = Pattern(width=10, height=10)
        undo = UndoManager()
        undo.set_pattern(pattern)

        undo.begin_batch("Erste Batch")
        undo.add_to_batch(PlaceStitchCommand(pattern, 0, 0, 0, 0))
        assert pattern.active_layer.get_stitch(0, 0) == 0  # sofort ausgefuehrt

        undo.begin_batch("Zweite Batch")  # re-entrant, ohne end_batch() dazwischen
        undo.add_to_batch(PlaceStitchCommand(pattern, 1, 1, 0, 0))
        undo.end_batch()

        # Beide Batches muessen in der Historie sein (die erste committet
        # durch den Re-Entrant-Guard, die zweite regulaer durch end_batch).
        assert undo.undo_count == 2

        undo.undo()  # macht die zweite Batch rueckgaengig
        assert pattern.active_layer.get_stitch(1, 1) is None
        assert pattern.active_layer.get_stitch(0, 0) == 0  # erste Batch bleibt bestehen

        undo.undo()  # macht die erste Batch rueckgaengig
        assert pattern.active_layer.get_stitch(0, 0) is None


class TestBackstitchCommands:
    """Tests für Rückstich-Commands."""

    def test_add_backstitch(self):
        """Test: Rückstich hinzufügen."""
        pattern = Pattern(width=10, height=10)
        cmd = AddBackstitchCommand(pattern, 0, 0, 4, 4, 0)
        cmd.execute()

        assert len(pattern.backstitches) == 1
        assert pattern.backstitches[0].x1 == 0
        assert pattern.backstitches[0].y1 == 0
        assert pattern.backstitches[0].x2 == 4
        assert pattern.backstitches[0].y2 == 4

    def test_undo_backstitch(self):
        """Test: Rückstich rückgängig machen."""
        pattern = Pattern(width=10, height=10)
        cmd = AddBackstitchCommand(pattern, 0, 0, 4, 4, 0)
        cmd.execute()
        cmd.undo()

        assert len(pattern.backstitches) == 0

    def test_remove_backstitch(self):
        """Test: Rückstich entfernen."""
        pattern = Pattern(width=10, height=10)
        bs = pattern.add_backstitch(0, 0, 4, 4, 0)

        cmd = RemoveBackstitchCommand(pattern, bs)
        cmd.execute()

        assert len(pattern.backstitches) == 0

    def test_remove_backstitch_undo(self):
        """Test: Entfernen rückgängig machen.

        Prüft auch Objekt-Identität: undo() muss das exakt gleiche
        Backstitch-Objekt wiederherstellen (via restore_backstitch()),
        nicht ein neu konstruiertes gleichwertiges Objekt -- sonst würde
        eine anderswo gehaltene Referenz (z.B. eine Selektion) auf das
        entfernte Objekt nach einem Undo ins Leere zeigen.
        """
        pattern = Pattern(width=10, height=10)
        bs = pattern.add_backstitch(0, 0, 4, 4, 0)

        cmd = RemoveBackstitchCommand(pattern, bs)
        cmd.execute()
        cmd.undo()

        assert len(pattern.backstitches) == 1
        assert pattern.backstitches[0] is bs


class TestLayerSnapshotCommand:
    """Regression: Plugins mutierten das Pattern komplett am Undo-System
    vorbei (direkter pattern.set_stitch()-Aufruf ohne jeden Command).
    LayerSnapshotCommand kapselt eine beliebige Aktion snapshot-basiert,
    damit auch nicht vorhersehbare Bulk-Mutationen undo-faehig werden."""

    def test_wraps_arbitrary_mutation_and_undoes_it(self):
        from pysticky.core import Thread

        pattern = Pattern(width=3, height=3)
        pattern.add_color(Thread.from_hex("Zweite Farbe", "#00FF00"))  # Index 1

        def action():
            for x in range(3):
                for y in range(3):
                    pattern.set_stitch(x, y, (x + y) % 2)

        cmd = LayerSnapshotCommand(
            pattern, layer_index=pattern.layer_stack.active_index, action=action
        )
        cmd.execute()

        layer = pattern.layer_stack.active_layer
        assert layer.get_stitch(0, 0) == 0
        assert layer.get_stitch(1, 0) == 1
        assert sum(e.stitch_count for e in pattern.color_entries) == 9

        cmd.undo()

        assert all(layer.get_stitch(x, y) is None for x in range(3) for y in range(3))
        assert sum(e.stitch_count for e in pattern.color_entries) == 0

    def test_redo_does_not_rerun_action(self):
        """Bei Redo darf `action` NICHT erneut aufgerufen werden -- sonst
        wuerde z.B. ein interaktives Plugin ein zweites Mal nach Eingaben
        fragen (und potenziell eine andere Antwort bekommen)."""
        pattern = Pattern(width=3, height=3)
        call_count = 0

        def action():
            nonlocal call_count
            call_count += 1
            pattern.set_stitch(0, 0, 0)

        cmd = LayerSnapshotCommand(
            pattern, layer_index=pattern.layer_stack.active_index, action=action
        )
        cmd.execute()  # erster Lauf
        assert call_count == 1
        cmd.undo()
        cmd.execute()  # Redo

        assert call_count == 1  # action() NICHT erneut aufgerufen
        assert pattern.layer_stack.active_layer.get_stitch(0, 0) == 0

    def test_rolls_back_on_action_error(self):
        """Stuerzt `action` nach teilweiser Mutation ab, darf das Pattern
        nicht in einem halb-veraenderten Zustand ohne Undo-Moeglichkeit
        haengen bleiben."""
        pattern = Pattern(width=3, height=3)
        pattern.set_stitch(1, 1, 0)  # bereits vorhandener Stich

        def crashing_action():
            pattern.set_stitch(0, 0, 0)  # partielle Mutation
            raise RuntimeError("boom")

        cmd = LayerSnapshotCommand(
            pattern, layer_index=pattern.layer_stack.active_index, action=crashing_action
        )
        with pytest.raises(RuntimeError):
            cmd.execute()

        layer = pattern.layer_stack.active_layer
        assert layer.get_stitch(0, 0) is None  # zurueckgerollt
        assert layer.get_stitch(1, 1) == 0  # unveraendert erhalten


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
