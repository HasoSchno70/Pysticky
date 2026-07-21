# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 16): OptimizationWorker._run_optimization()/
_run_comparison() hatten UEBERHAUPT KEIN try/except um optimizer.optimize()/
compare_strategies(). Ein unerwarteter Fehler dort liess weder finished
noch comparison_finished feuern -- der QThread waere nie fertig geworden,
und stitch_path_dialog.py haette dauerhaft im "laeuft"-Zustand haengen
bleiben (Buttons deaktiviert, Fortschrittsbalken sichtbar, keine
Abbruchmoeglichkeit). Schlimmste bisher gefundene Auspraegung dieser
Bug-Klasse: komplette Abwesenheit jeder Fehlerbehandlung, nicht nur ein zu
enger except-Filter (vgl. oxs_io.py Runde 11, Bildimport-Worker Runde 14).
"""

import pytest

from pysticky.core import Pattern, Thread

pytestmark = pytest.mark.usefixtures("qtbot")


def _pattern_with_stitches():
    p = Pattern(name="Opt-Test", width=10, height=10)
    p.color_entries.clear()
    p.add_color(Thread.from_hex("Rot", "#FF0000"))
    p.set_stitch(0, 0, 0)
    p.set_stitch(5, 5, 0)
    return p


def test_run_optimization_emits_finished_none_on_unexpected_error(qtbot, monkeypatch):
    from pysticky.core import OptimizationStrategy
    from pysticky.ui.workers.optimization_worker import OptimizationWorker

    worker = OptimizationWorker(_pattern_with_stitches())

    def boom(*args, **kwargs):
        raise RuntimeError("unerwarteter interner Fehler")

    from pysticky.ui.workers import optimization_worker as mod

    monkeypatch.setattr(
        mod,
        "StitchPathOptimizer",
        lambda *a, **k: type("Boom", (), {"optimize": staticmethod(boom)})(),
    )

    received = []
    worker.finished.connect(lambda r: received.append(r))

    worker._run_optimization(OptimizationStrategy.NEAREST_NEIGHBOR, 14)

    assert received == [None]


def test_run_comparison_emits_comparison_finished_none_on_unexpected_error(qtbot, monkeypatch):
    from pysticky.ui.workers import optimization_worker as mod
    from pysticky.ui.workers.optimization_worker import OptimizationWorker

    worker = OptimizationWorker(_pattern_with_stitches())

    def boom(*args, **kwargs):
        raise RuntimeError("unerwarteter interner Fehler")

    monkeypatch.setattr(mod, "compare_strategies", boom)

    received = []
    worker.comparison_finished.connect(lambda r: received.append(r))

    worker._run_comparison(14)

    assert received == [None]


def test_run_optimization_still_emits_real_result_on_success(qtbot):
    from pysticky.core import OptimizationStrategy
    from pysticky.ui.workers.optimization_worker import OptimizationWorker

    worker = OptimizationWorker(_pattern_with_stitches())

    received = []
    worker.finished.connect(lambda r: received.append(r))

    worker._run_optimization(OptimizationStrategy.NEAREST_NEIGHBOR, 14)

    assert len(received) == 1
    assert received[0] is not None
