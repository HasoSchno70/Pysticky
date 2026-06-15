# -*- coding: utf-8 -*-
"""
Tests für das Undo-System.
"""

import pytest

from pysticky.core import (
    AddBackstitchCommand,
    BatchStitchCommand,
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
        """Test: Entfernen rückgängig machen."""
        pattern = Pattern(width=10, height=10)
        bs = pattern.add_backstitch(0, 0, 4, 4, 0)

        cmd = RemoveBackstitchCommand(pattern, bs)
        cmd.execute()
        cmd.undo()

        assert len(pattern.backstitches) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
