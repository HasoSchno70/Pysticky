# -*- coding: utf-8 -*-
"""
Regressionstest: CropPreviewWidget.set_crop() klemmte x1/y1/x2/y2 jeweils
einzeln auf [0,1], erzwang aber nie x1<=x2/y1<=y2 -- anders als der Maus-
Drag-Pfad, der dieses Invariant immer einhaelt. Eine invertierte
source_image_crop aus einer beschaedigten/handbearbeiteten .pxs-Datei
(file_io.py laedt das ohne Validierung) konnte so unbemerkt bis zu
core/image_import.py durchgereicht werden.
"""

from pysticky.ui.widgets.crop_preview import CropPreviewWidget


def test_set_crop_normalizes_inverted_coordinates(qtbot):
    widget = CropPreviewWidget()
    qtbot.addWidget(widget)

    widget.set_crop(0.8, 0.7, 0.2, 0.1)  # x1>x2, y1>y2 -- invertiert

    x1, y1, x2, y2 = widget.get_crop()
    assert x1 <= x2
    assert y1 <= y2
    assert (x1, y1, x2, y2) == (0.2, 0.1, 0.8, 0.7)


def test_set_crop_accepts_normal_order_unchanged(qtbot):
    widget = CropPreviewWidget()
    qtbot.addWidget(widget)

    widget.set_crop(0.1, 0.2, 0.9, 0.8)

    assert widget.get_crop() == (0.1, 0.2, 0.9, 0.8)


def test_set_crop_still_clamps_out_of_range_values(qtbot):
    widget = CropPreviewWidget()
    qtbot.addWidget(widget)

    widget.set_crop(-0.5, -0.2, 1.5, 2.0)

    x1, y1, x2, y2 = widget.get_crop()
    assert (x1, y1, x2, y2) == (0.0, 0.0, 1.0, 1.0)
