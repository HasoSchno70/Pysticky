# -*- coding: utf-8 -*-
"""
Undo/Redo-Stresstest mit realistischen, mehrstufigen Operationssequenzen.

Ergänzt tests/test_undo.py (das einzelne Commands isoliert prüft) um
Sequenz-Interaktionen, die in echter Nutzung vorkommen, aber in isolierten
Einzeltests nicht auftauchen: Interleaving verschiedener Command-Typen,
tiefe Batch-Verschachtelung waehrend einer Struktur-Aenderung, Undo ueber
eine bereits geleerte Historie hinaus, max_history-Kappung mitten in einer
langen Sequenz, und die Interaktion von Pattern.convert_to_mode() mit dem
Undo-System.

Runde (Clean-Code-Audit, Undo/Redo-Sequenz-Stresstest): 4 der 5 geprüften
Szenarien verhielten sich bereits korrekt (siehe TestScenario1/2/3/4 unten,
reine Charakterisierungstests ohne Codeänderung). Szenario 5 deckte einen
echten Bug auf: Pattern.convert_to_mode() läuft komplett am Undo-System
vorbei, obwohl es entry.is_diamond/is_bead-Flags UND die Stich-Typen
bereits platzierter Zellen umschreibt (_restamp_stitch_type_for_color()).
Vor der Konvertierung ausgeführte PlaceStitchCommand/RemoveStitchCommand-
Einträge frieren ihren alten Stich-Typ (z.B. DIAMOND=11) ein; ein
Undo/Redo NACH einer Konvertierung schreibt diesen veralteten Stich-Typ
zurück, obwohl die betroffene Farbe inzwischen gar nicht mehr
is_diamond/is_bead ist. Der Renderer prüft `stype == 11` UNGEGATET
(ui/canvas/mixins/rendering_mixin.py) -- eine so wiederhergestellte Zelle
zeigt dauerhaft einen Diamant-Drill in einem "stitch"-Modus-Muster.
Fix: MainWindow._on_toggle_diamond_view() (ui/handlers/view_handlers.py)
leert jetzt den Undo-Verlauf nach jeder erfolgreichen Konvertierung, exakt
wie es _on_layer_structure_changed/_on_merge_similar_colors/_on_manage_colors
für dieselbe Fehlerklasse bereits tun.
"""

import pytest

from pysticky.core import (
    AddBackstitchCommand,
    Pattern,
    PlaceStitchCommand,
    RemoveStitchCommand,
    Thread,
    ThreadColor,
    UndoManager,
)
from pysticky.core.stitch import StitchType


class TestScenario1Interleaving:
    """Undo/Redo-Interleaving zwischen strukturell verschiedenen Command-
    Typen: eine neue Aktion nach einem Undo muss den Redo-Stack konsequent
    leeren, auch wenn die neue Aktion ein völlig anderer Command-Typ ist
    als der gerade rückgängig gemachte."""

    def test_new_action_after_undo_of_different_command_type_clears_redo(self):
        pattern = Pattern(width=10, height=10)
        pattern.add_color(Thread(name="rot", color=ThreadColor(255, 0, 0)))
        undo = UndoManager()
        undo.set_pattern(pattern)

        undo.execute(PlaceStitchCommand(pattern, 1, 1, 0, 0))
        undo.execute(AddBackstitchCommand(pattern, 0, 0, 2, 2, 0))
        undo.undo()  # macht Backstitch rueckgaengig
        assert undo.can_redo is True

        # Neue, ANDERE Aktion (RemoveStitchCommand statt Backstitch)
        undo.execute(RemoveStitchCommand(pattern, 1, 1, 0))

        assert undo.can_redo is False, (
            "Redo-Stack haette nach einer neuen Aktion geleert werden muessen"
        )
        assert undo.redo_count == 0


class TestScenario2NestedBatches:
    """Tiefe Batch-Verschachtelung (3+ Ebenen) + eine Struktur-Aenderung
    (undo_manager.clear()) waehrend die innerste Batch noch offen ist."""

    def test_deeply_nested_reentrant_batches_commit_sequentially(self):
        pattern = Pattern(width=10, height=10)
        pattern.add_color(Thread(name="rot", color=ThreadColor(255, 0, 0)))
        undo = UndoManager()
        undo.set_pattern(pattern)

        undo.begin_batch("Batch A")
        undo.add_to_batch(PlaceStitchCommand(pattern, 0, 0, 0, 0))
        undo.begin_batch("Batch B")  # re-entrant -> committet Batch A
        undo.add_to_batch(PlaceStitchCommand(pattern, 1, 1, 0, 0))
        undo.begin_batch("Batch C")  # re-entrant -> committet Batch B
        undo.add_to_batch(PlaceStitchCommand(pattern, 2, 2, 0, 0))

        # A und B wurden bereits committet, C ist noch offen.
        assert undo.undo_count == 2
        assert undo.in_batch is True

        # Alle drei Grid-Mutationen sind trotzdem angewendet (add_to_batch
        # fuehrt sofort aus).
        assert pattern.active_layer.get_stitch(0, 0) == 0
        assert pattern.active_layer.get_stitch(1, 1) == 0
        assert pattern.active_layer.get_stitch(2, 2) == 0

    def test_clear_during_open_batch_discards_batch_without_crash(self):
        """Struktur-Aenderung (undo_manager.clear()) waehrend eine Batch
        offen ist: die Batch wird ohne Undo verworfen (dokumentiertes
        Verhalten von UndoManager.clear()), ihre bereits angewendeten
        Grid-Mutationen bleiben bestehen. Ein spaeterer end_batch()-Aufruf
        der alten Call-Site darf nicht crashen oder einen Phantom-Eintrag
        erzeugen."""
        pattern = Pattern(width=10, height=10)
        pattern.add_color(Thread(name="rot", color=ThreadColor(255, 0, 0)))
        undo = UndoManager()
        undo.set_pattern(pattern)

        undo.begin_batch("Batch offen")
        undo.add_to_batch(PlaceStitchCommand(pattern, 2, 2, 0, 0))
        assert undo.in_batch is True

        undo.clear()  # simuliert _on_layer_structure_changed() mitten in der Batch
        assert undo.in_batch is False
        assert undo.undo_count == 0

        undo.end_batch()  # alte Call-Site weiss nichts von clear()
        assert undo.undo_count == 0, "end_batch() nach clear() darf keinen Eintrag erzeugen"
        # Mutation von vor dem clear() bleibt bestehen (kein Rollback vorgesehen).
        assert pattern.active_layer.get_stitch(2, 2) == 0


class TestScenario3UndoPastStructureChange:
    """Undo nach einer Struktur-Aenderung, die den Stack schon geleert hat,
    gefolgt von neuen Aktionen, gefolgt von mehr undo()-Aufrufen als es
    Eintraege gibt -- darf nicht crashen oder can_undo/undo() inkonsistent
    machen."""

    def test_repeated_undo_past_exhaustion_after_structure_change(self):
        pattern = Pattern(width=10, height=10)
        pattern.add_color(Thread(name="rot", color=ThreadColor(255, 0, 0)))
        pattern.layer_stack.add_layer("Layer B")

        undo = UndoManager()
        undo.set_pattern(pattern)

        undo.execute(PlaceStitchCommand(pattern, 0, 0, 0, 0))  # Layer A (Index 0)

        pattern.layer_stack.remove_layer(0)  # Layer A entfernt -> Indizes verschieben sich
        undo.clear()  # etablierter Mechanismus (_on_layer_structure_changed)
        assert undo.can_undo is False

        undo.execute(PlaceStitchCommand(pattern, 1, 1, 0, 0))  # neue Aktion auf verbliebenem Layer
        assert undo.undo_count == 1

        # Mehr undo()-Aufrufe als Eintraege vorhanden
        results = [undo.undo() for _ in range(5)]
        assert results == [True, False, False, False, False]
        assert undo.can_undo is False
        assert undo.undo_count == 0


class TestScenario4MaxHistoryCapping:
    """max_history-Kappung mitten in einer langen Sequenz von 150+
    Einzel-Commands: aelteste Eintraege muessen korrekt herausfallen, und
    ein Undo bis zum Anschlag muss sauber stoppen ohne inkonsistenten
    redo_stack."""

    def test_capped_history_undoes_exactly_max_history_entries(self):
        pattern = Pattern(width=20, height=20)
        pattern.add_color(Thread(name="rot", color=ThreadColor(255, 0, 0)))
        undo = UndoManager(max_history=100)
        undo.set_pattern(pattern)

        for i in range(150):
            x, y = i % 20, i // 20
            undo.execute(PlaceStitchCommand(pattern, x, y, 0, 0))

        assert undo.undo_count == 100, "deque(maxlen=100) haette die aeltesten 50 verwerfen muessen"

        # Die aeltesten 50 Zellen (i=0..49) sind nicht mehr rueckgaengig
        # machbar -- ihre Stiche bleiben nach vollstaendigem Undo bestehen.
        undo_calls = 0
        while undo.undo():
            undo_calls += 1
        assert undo_calls == 100
        assert undo.can_undo is False
        assert undo.redo_count == 100, (
            "redo_stack muss konsistent alle 100 rueckgaengig gemachten Commands halten"
        )

        # Weiterer undo()-Aufruf nach Erschoepfung darf nicht crashen.
        assert undo.undo() is False

        for i in range(50):
            x, y = i % 20, i // 20
            assert pattern.active_layer.get_stitch(x, y) == 0, (
                "Die aeltesten 50 Stiche wurden nie in die Historie aufgenommen "
                "und muessen daher stehen bleiben"
            )
        for i in range(50, 150):
            x, y = i % 20, i // 20
            assert pattern.active_layer.get_stitch(x, y) is None


class TestScenario5ConvertToModeVsUndo:
    """Pattern.convert_to_mode() laeuft komplett am Undo-System vorbei --
    kein Command, kein undo_manager.clear(). Ein Undo NACH einer
    Konvertierung, das VOR die Konvertierung zurueckgeht, schreibt einen
    veralteten Stich-Typ (z.B. DIAMOND=11) auf eine Zelle, deren Farbe
    inzwischen nicht mehr is_diamond ist."""

    def test_core_reproduction_stale_stitch_type_after_undo_past_conversion(self):
        """Reine Kern-Reproduktion OHNE die UI-Fix-Ebene: zeigt, dass
        convert_to_mode() selbst keinerlei Undo-Interaktion hat und ein
        danach ausgefuehrtes undo() eine inkonsistente Zelle erzeugen kann.
        Dies ist die Begruendung fuer den Fix in view_handlers.py (siehe
        TestDiamondViewToggleClearsUndo weiter unten fuer die eigentliche
        Regression gegen den Fix)."""
        pattern = Pattern(width=10, height=10)  # mode="stitch"
        pattern.add_color(Thread(name="rot", color=ThreadColor(255, 0, 0)))  # Farbe 1

        undo = UndoManager()
        undo.set_pattern(pattern)

        undo.execute(PlaceStitchCommand(pattern, 5, 5, 0, 0))
        pattern.convert_to_mode("diamond")  # restamp setzt stype(5,5) auf DIAMOND=11
        assert pattern.active_layer.get_stitch_type(5, 5) == StitchType.DIAMOND.value

        cmd_overwrite = PlaceStitchCommand(pattern, 5, 5, 1, 0)
        undo.execute(cmd_overwrite)  # faengt _old_stitch_type=11 frisch/korrekt ein

        pattern.convert_to_mode("stitch")  # is_diamond wird False, restamp -> stype(5,5)=0
        assert pattern.color_entries[0].is_diamond is False
        assert pattern.color_entries[1].is_diamond is False

        # cmd_overwrite rueckgaengig -> schreibt den eingefrorenen alten Typ (11) zurueck
        undo.undo()

        color_after = pattern.active_layer.get_stitch(5, 5)
        stype_after = pattern.active_layer.get_stitch_type(5, 5)
        assert color_after == 0
        # Ohne Undo-Clear NACH der Konvertierung ist genau das der Bug:
        # DIAMOND-Typ auf einer Nicht-Diamond-Farbe im "stitch"-Modus.
        assert stype_after == StitchType.DIAMOND.value
        assert pattern.color_entries[color_after].is_diamond is False


@pytest.fixture
def main_window(qtbot):
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication([])

    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    # Siehe test_layer_structure_undo_clear.py::main_window fuer die Begruendung.
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    return w


class TestDiamondViewToggleClearsUndo:
    """Regressionstest gegen den Fix in view_handlers.py::_on_toggle_diamond_view:
    das Umschalten auf Diamond-Painting-Ansicht (und zurueck) konvertiert
    das Pattern per Pattern.convert_to_mode() -- muss die Undo-Historie
    genauso leeren wie eine Ebenen-Struktur-Aenderung oder die Farbpaletten-
    Dialoge (siehe test_layer_structure_undo_clear.py fuer das analoge
    Muster bei Ebenen)."""

    def test_toggling_diamond_view_clears_undo_history(self, main_window):
        from pysticky.core import PlaceStitchCommand

        assert len(main_window.current_pattern.color_entries) > 0
        cmd = PlaceStitchCommand(main_window.current_pattern, 0, 0, 0, 0)
        main_window.undo_manager.execute(cmd)
        assert main_window.undo_manager.can_undo is True

        main_window.action_diamond_view.trigger()  # -> _on_toggle_diamond_view

        assert main_window.undo_manager.can_undo is False, (
            "Regression: convert_to_mode() aendert is_diamond-Flags und Stich-Typen "
            "bereits platzierter Zellen -- gespeicherte Undo-Commands mit eingefrorenen "
            "alten Stich-Typen wuerden sonst nach Undo eine inkonsistente Zelle erzeugen."
        )

    def test_toggling_diamond_view_and_back_clears_undo_history_each_time(self, main_window):
        from pysticky.core import PlaceStitchCommand

        main_window.action_diamond_view.trigger()  # stitch -> diamond

        cmd = PlaceStitchCommand(main_window.current_pattern, 1, 1, 0, 0)
        main_window.undo_manager.execute(cmd)
        assert main_window.undo_manager.can_undo is True

        main_window.action_diamond_view.trigger()  # diamond -> stitch

        assert main_window.undo_manager.can_undo is False
