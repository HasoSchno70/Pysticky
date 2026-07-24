# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 69): `ColorSwatch` (ui/widgets/color_bar.py) ist das
tatsaechliche Drop-Ziel fuer den Drag&Drop-Farbtausch (SWAP_MIME), hatte
aber KEIN eigenes `dragMoveEvent`. Ohne diesen Override greift Qts
QWidget-Standardimplementierung, die das Event ignoriert (`event.ignore()`).

`dragEnterEvent` akzeptiert zwar beim ERSTEN Betreten eines Swatches, aber
Qt liefert fuer JEDE weitere Mausbewegung *innerhalb* desselben Widgets ein
neues `dragMoveEvent` (nicht erneut `dragEnterEvent`). Bei einer echten,
von Hand ausgefuehrten Drag-Bewegung steht die Maus so gut wie nie exakt
still -- jede dieser Bewegungen wurde also stillschweigend abgelehnt. Qts
Drag-Manager merkt sich an der aktuellen Position dadurch "abgelehnt" und
liefert beim Loslassen der Maustaste gar kein `dropEvent` mehr aus. Der
Farbtausch per Drag&Drop war dadurch **nur** moeglich, wenn man die
Maustaste exakt auf dem Eintritts-Pixel losliess -- in der Praxis quasi nie
der Fall. Fix: `ColorSwatch.dragMoveEvent()` akzeptiert denselben SWAP_MIME-
Payload wie `dragEnterEvent()`/`dropEvent()` (jetzt ueber die gemeinsame
Hilfsmethode `_swap_source_index()`).
"""

from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent

from pysticky.core import ColorEntry, Thread
from pysticky.ui.widgets.color_bar import SWAP_MIME, ColorSwatch


def _make_swatch(index: int) -> ColorSwatch:
    entry = ColorEntry(symbol="A", thread=Thread.from_hex("Rot", "#FF0000"))
    swatch = ColorSwatch(index, entry)
    swatch.resize(48, 62)
    return swatch


def _swap_mime(src_index: int) -> QMimeData:
    md = QMimeData()
    md.setData(SWAP_MIME, str(src_index).encode("utf-8"))
    return md


def test_drag_move_event_accepts_valid_swap_source(qtbot):
    """Kernregression: ein dragMoveEvent (nicht nur dragEnterEvent) mit
    gueltigem, abweichendem Quell-Index MUSS akzeptiert werden -- sonst
    bricht Qt den Drop bei jeder Mausbewegung innerhalb des Swatches ab."""
    swatch = _make_swatch(index=1)
    qtbot.addWidget(swatch)
    md = _swap_mime(0)

    move_event = QDragMoveEvent(
        QPoint(20, 20),
        Qt.DropAction.MoveAction,
        md,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    swatch.dragMoveEvent(move_event)

    assert move_event.isAccepted(), (
        "dragMoveEvent muss einen gueltigen SWAP_MIME-Drop akzeptieren, sonst "
        "verwirft Qt den Drag bei jeder Mausbewegung im Swatch"
    )


def test_drag_move_event_rejects_self_swap(qtbot):
    """Ein Swatch darf keinen Swap mit sich selbst akzeptieren (Quell-Index
    == eigener Index)."""
    swatch = _make_swatch(index=2)
    qtbot.addWidget(swatch)
    md = _swap_mime(2)

    move_event = QDragMoveEvent(
        QPoint(5, 5),
        Qt.DropAction.MoveAction,
        md,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    swatch.dragMoveEvent(move_event)

    assert not move_event.isAccepted()


def test_drag_move_event_rejects_foreign_mime_type(qtbot):
    """Ein dragMoveEvent ohne SWAP_MIME (z.B. ein Palette-Thread-Drag ueber
    ein Swatch hinweg) darf nicht faelschlich akzeptiert werden."""
    swatch = _make_swatch(index=0)
    qtbot.addWidget(swatch)
    md = QMimeData()
    md.setData("application/x-pysticky-thread", b"Foo|123|Rot|#FF0000")

    move_event = QDragMoveEvent(
        QPoint(5, 5),
        Qt.DropAction.MoveAction,
        md,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    swatch.dragMoveEvent(move_event)

    assert not move_event.isAccepted()


def test_full_enter_move_drop_sequence_completes(qtbot):
    """Simuliert die reale Ereignis-Abfolge einer Handbewegung: enter, dann
    (mind.) eine move innerhalb desselben Swatches, dann drop -- muss am
    Ende swap_dropped mit (src, dst) emittieren."""
    swatch = _make_swatch(index=3)
    qtbot.addWidget(swatch)
    md = _swap_mime(1)

    received: list[tuple[int, int]] = []
    swatch.swap_dropped.connect(lambda src, dst: received.append((src, dst)))

    enter_event = QDragEnterEvent(
        QPointF(10, 10).toPoint(),
        Qt.DropAction.MoveAction,
        md,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    swatch.dragEnterEvent(enter_event)
    assert enter_event.isAccepted()

    # Realistische Mausbewegung innerhalb des Swatches nach dem Eintritt.
    move_event = QDragMoveEvent(
        QPoint(12, 13),
        Qt.DropAction.MoveAction,
        md,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    swatch.dragMoveEvent(move_event)
    assert move_event.isAccepted()

    drop_event = QDropEvent(
        QPointF(12, 13),
        Qt.DropAction.MoveAction,
        md,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    swatch.dropEvent(drop_event)

    assert received == [(1, 3)]
