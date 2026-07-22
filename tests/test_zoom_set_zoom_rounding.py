# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 24): ZoomMixin.set_zoom() nutzte int() statt
round(), das immer Richtung 0 abrundet. Ein angefragter Zoom von z.B.
133% (factor=1.33) ergab int(20*1.33)=int(26.6)=26 statt der
naheliegenden 27 -- get_zoom_percent() meldete danach 130% statt der
angefragten 133%, kein sauberer Roundtrip.
"""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def test_set_zoom_rounds_instead_of_truncating(qtbot):
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)

    canvas.set_zoom(1.33)

    # DEFAULT_CELL_SIZE * 1.33 = 26.6 -> round() = 27, int() haette 26 ergeben.
    assert canvas._cell_size == round(canvas.DEFAULT_CELL_SIZE * 1.33)
    assert canvas._cell_size != int(canvas.DEFAULT_CELL_SIZE * 1.33)
