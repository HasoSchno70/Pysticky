# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 14): _ImageImportWorker.run() fing nur
(OSError, ValueError) -- jeder andere unerwartete Fehler aus
import_image() (z.B. PIL.Image.DecompressionBombError bei einem riesigen
Quellbild, oder ein interner Fehler in der Dithering-/Quantisierungs-
Pipeline) liess weder finished noch error feuern. dialog.py::_on_import()
verbindet Thread-quit()/deleteLater() nur an diese beiden Signale, der
QThread waere also nie fertig geworden und der modale Fortschrittsdialog
haette sich dauerhaft nicht mehr schliessen lassen (_import_running()
bleibt True). Gleiche Bug-Klasse wie oxs_io.py in Runde 11.
"""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def test_worker_emits_error_on_unexpected_exception(qtbot, monkeypatch):
    from pysticky.ui.dialogs.image_import import worker as worker_mod

    def boom(*args, **kwargs):
        raise RuntimeError("unerwarteter interner Fehler")

    monkeypatch.setattr(worker_mod, "import_image", boom)

    w = worker_mod._ImageImportWorker("dummy.png", settings=None, crop=None)

    finished_calls = []
    error_calls = []
    w.finished.connect(lambda p: finished_calls.append(p))
    w.error.connect(lambda msg: error_calls.append(msg))

    w.run()

    assert finished_calls == []
    assert len(error_calls) == 1
    assert "unerwarteter interner Fehler" in error_calls[0]


def test_worker_still_emits_error_on_known_exceptions(qtbot, monkeypatch):
    """Regressionsschutz: der bestehende (OSError, ValueError)-Pfad darf
    durch den neuen Catch-all nicht verdraengt werden."""
    from pysticky.ui.dialogs.image_import import worker as worker_mod

    def boom(*args, **kwargs):
        raise ValueError("ungueltige Einstellungen")

    monkeypatch.setattr(worker_mod, "import_image", boom)

    w = worker_mod._ImageImportWorker("dummy.png", settings=None, crop=None)
    error_calls = []
    w.error.connect(lambda msg: error_calls.append(msg))

    w.run()

    assert error_calls == ["ungueltige Einstellungen"]
