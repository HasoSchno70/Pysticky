"""
Layer-Panel zur Verwaltung von Ebenen mit Drag & Drop.
"""

from PySide6.QtCore import QMimeData, QPoint, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QDrag,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QIcon,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPalette,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ...core.i18n import t
from ...core.layer import Layer, LayerStack
from ..styles import THEME


def _make_eye_icon(visible: bool, fg: QColor, size: int = 20) -> QIcon:
    """Zeichnet ein Auge-Symbol — kein Emoji-Rendering noetig, plattform-unabhaengig."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen_w = max(1.5, size / 12)
    p.setPen(QPen(fg, pen_w))
    # Aeussere Augen-Form: zwei aufeinander treffende Boegen
    margin = size * 0.12
    rect_h = size * 0.55
    cx = size / 2
    cy = size / 2
    path = QPainterPath()
    path.moveTo(margin, cy)
    path.quadTo(cx, cy - rect_h / 2 - size * 0.05, size - margin, cy)
    path.quadTo(cx, cy + rect_h / 2 + size * 0.05, margin, cy)
    p.drawPath(path)
    # Pupille (gefuellter Kreis in der Mitte)
    pupil_r = size * 0.18
    p.setBrush(fg)
    p.drawEllipse(int(cx - pupil_r), int(cy - pupil_r), int(2 * pupil_r), int(2 * pupil_r))
    # Wenn versteckt: Schraegstrich durchs Auge
    if not visible:
        p.setPen(QPen(fg, pen_w + 0.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(int(margin), int(size - margin), int(size - margin), int(margin))
    p.end()
    return QIcon(pm)


def _make_lock_icon(locked: bool, fg: QColor, size: int = 20) -> QIcon:
    """Zeichnet ein Schloss-Symbol selbst (gefuellt, offen mit gehobenem Buegel)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen_w = max(1.5, size / 12)

    # Buegel (Shackle) — geoeffnet, wenn nicht locked, leicht nach oben/rechts gekippt
    p.setPen(QPen(fg, pen_w))
    p.setBrush(Qt.BrushStyle.NoBrush)
    shackle_w = size * 0.55
    shackle_h = size * 0.45
    shackle_x = (size - shackle_w) / 2
    if locked:
        shackle_y = size * 0.15
        p.drawArc(
            int(shackle_x), int(shackle_y), int(shackle_w), int(shackle_h * 1.6), 0 * 16, 180 * 16
        )
    else:
        # Geoeffnet: Buegel nach rechts geneigt, sieht nicht geschlossen aus
        shackle_y = size * 0.10
        # Linker Pfosten lang, rechter Pfosten als kurze Linie nach oben
        path = QPainterPath()
        path.moveTo(shackle_x, size * 0.50)
        path.lineTo(shackle_x, shackle_y + shackle_h / 2)
        path.arcTo(shackle_x, shackle_y, shackle_w, shackle_h, 180, -180)
        path.lineTo(shackle_x + shackle_w, shackle_y + shackle_h * 0.1)
        p.drawPath(path)

    # Korpus (gefuelltes Rechteck unter dem Buegel)
    body_h = size * 0.42
    body_w = size * 0.72
    body_x = (size - body_w) / 2
    body_y = size * 0.50
    p.setPen(QPen(fg, pen_w))
    p.setBrush(QBrush(fg))
    p.drawRoundedRect(
        int(body_x), int(body_y), int(body_w), int(body_h), max(1.0, size / 14), max(1.0, size / 14)
    )
    p.end()
    return QIcon(pm)


class LayerListItem(QWidget):
    """Widget für einen Layer-Eintrag."""

    visibility_changed = Signal(bool)
    lock_changed = Signal(bool)

    def __init__(self, layer: Layer, index: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layer: Layer = layer
        self._index: int = index
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # Drag-Handle
        self.drag_handle = QLabel("☰")
        self.drag_handle.setFixedWidth(20)
        self.drag_handle.setStyleSheet(
            f"color: {THEME.text_disabled}; font-size: 14px; background: transparent;"
        )
        self.drag_handle.setToolTip(t("Ziehen zum Verschieben"))
        layout.addWidget(self.drag_handle)

        # Sichtbarkeits-Button — gezeichnetes Auge-Icon (kein Emoji)
        self.btn_visible = QPushButton()
        self.btn_visible.setFixedSize(34, 30)
        self.btn_visible.setIconSize(QSize(20, 20))
        self.btn_visible.setCheckable(True)
        self.btn_visible.setChecked(self._layer.visible)
        self.btn_visible.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_visible.setToolTip(t("Ebene anzeigen / verstecken"))
        self.btn_visible.toggled.connect(self._on_visibility_toggled)
        layout.addWidget(self.btn_visible)

        # Lock-Button — gezeichnetes Schloss-Icon
        self.btn_locked = QPushButton()
        self.btn_locked.setFixedSize(34, 30)
        self.btn_locked.setIconSize(QSize(20, 20))
        self.btn_locked.setCheckable(True)
        self.btn_locked.setChecked(self._layer.locked)
        self.btn_locked.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_locked.setToolTip(
            t("Ebene sperren (gegen versehentliches Bearbeiten) / entsperren")
        )
        self.btn_locked.toggled.connect(self._on_lock_toggled)
        layout.addWidget(self.btn_locked)

        # Name
        self.lbl_name = QLabel(self._layer.name)
        self.lbl_name.setMinimumWidth(60)
        layout.addWidget(self.lbl_name, 1)

        # Stichzahl
        self.lbl_count = QLabel(f"{self._layer.count_stitches()}")
        self.lbl_count.setFixedWidth(45)
        self.lbl_count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.lbl_count)

        self.setMinimumHeight(40)
        self._apply_styles()

    def _apply_styles(self) -> None:
        self.drag_handle.setStyleSheet(
            f"color: {THEME.text_disabled}; font-size: 14px; background: transparent;"
        )

        # Sichtbarkeits-Button: kraeftig gruen wenn an, hell-grau wenn aus.
        # Icon-Farbe kontrastiert immer zum Hintergrund.
        vis_on = self._layer.visible
        if vis_on:
            self.btn_visible.setIcon(_make_eye_icon(True, QColor(THEME.bg_dark)))
            self.btn_visible.setStyleSheet(f"""
                QPushButton {{
                    background: {THEME.accent_primary};
                    border: 1px solid {THEME.accent_primary};
                    border-radius: 6px;
                    padding: 0;
                }}
                QPushButton:hover {{
                    background: {THEME.success};
                    border-color: {THEME.success};
                }}
            """)
        else:
            self.btn_visible.setIcon(_make_eye_icon(False, QColor(THEME.text_disabled)))
            self.btn_visible.setStyleSheet(f"""
                QPushButton {{
                    background: {THEME.bg_light};
                    border: 1px solid {THEME.border_medium};
                    border-radius: 6px;
                    padding: 0;
                }}
                QPushButton:hover {{
                    background: {THEME.bg_lighter};
                    border-color: {THEME.accent_primary};
                }}
            """)

        # Lock-Button: rot wenn gesperrt (Icon weiss), neutral wenn offen.
        locked = self._layer.locked
        if locked:
            self.btn_locked.setIcon(_make_lock_icon(True, QColor("white")))
            self.btn_locked.setStyleSheet(f"""
                QPushButton {{
                    background: {THEME.error};
                    border: 1px solid {THEME.error};
                    border-radius: 6px;
                    padding: 0;
                }}
                QPushButton:hover {{
                    background: {THEME.warning};
                    border-color: {THEME.warning};
                }}
            """)
        else:
            self.btn_locked.setIcon(_make_lock_icon(False, QColor(THEME.text_secondary)))
            self.btn_locked.setStyleSheet(f"""
                QPushButton {{
                    background: {THEME.bg_light};
                    border: 1px solid {THEME.border_medium};
                    border-radius: 6px;
                    padding: 0;
                }}
                QPushButton:hover {{
                    background: {THEME.bg_lighter};
                    border-color: {THEME.warning};
                }}
            """)

        self.lbl_name.setStyleSheet(
            f"font-weight: 600; font-size: 12px; color: {THEME.text_primary}; background: transparent;"
        )
        self.lbl_count.setStyleSheet(
            f"color: {THEME.accent_primary}; font-size: 11px; font-weight: 600; background: transparent;"
        )

    def sizeHint(self) -> QSize:
        return QSize(200, 44)

    @property
    def layer_index(self) -> int:
        return self._index

    def update_layer(self, layer: Layer, index: int) -> None:
        """Aktualisiert das Widget mit neuen Layer-Daten."""
        self._layer = layer
        self._index = index
        self.btn_visible.setChecked(layer.visible)
        self.btn_locked.setChecked(layer.locked)
        self.lbl_name.setText(t(layer.name))
        self.lbl_count.setText(f"{layer.count_stitches()}")
        self._apply_styles()

    def _on_visibility_toggled(self, checked: bool) -> None:
        self._layer.visible = checked
        self._apply_styles()
        self.visibility_changed.emit(checked)

    def _on_lock_toggled(self, checked: bool) -> None:
        self._layer.locked = checked
        self._apply_styles()
        self.lock_changed.emit(checked)


class DraggableLayerList(QListWidget):
    """QListWidget mit Drag & Drop für Layer-Neuordnung und Zusammenführen."""

    layers_reordered = Signal(int, int)
    layers_merge_requested = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._drag_start_pos: QPoint | None = None
        self._dragged_item: QListWidgetItem | None = None
        self._drop_indicator_index: int = -1
        self._merge_target_index: int = -1

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(False)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self._apply_theme()

    def _apply_theme(self) -> None:
        self.setStyleSheet(f"""
            QListWidget {{
                background: {THEME.bg_dark};
                border: 1px solid {THEME.border_medium};
                border-radius: 6px;
            }}
            QListWidget::item {{
                background: {THEME.bg_light};
                border: 1px solid {THEME.border_medium};
                border-radius: 4px;
                margin: 2px 4px;
            }}
            QListWidget::item:selected {{
                background: {THEME.bg_lighter};
                border: 2px solid {THEME.accent_primary};
            }}
            QListWidget::item:hover {{
                background: {THEME.bg_lighter};
                border-color: {THEME.border_light};
            }}
        """)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
            item = self.itemAt(event.pos())
            if item:
                self._dragged_item = item
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return

        if not self._drag_start_pos or not self._dragged_item:
            super().mouseMoveEvent(event)
            return

        if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
            super().mouseMoveEvent(event)
            return

        drag = QDrag(self)
        mime_data = QMimeData()

        source_row = self.row(self._dragged_item)
        mime_data.setData("application/x-layer-index", str(source_row).encode())
        drag.setMimeData(mime_data)

        widget = self.itemWidget(self._dragged_item)
        if widget:
            pixmap = QPixmap(widget.size())
            pixmap.fill(QColor(THEME.bg_light))
            painter = QPainter(pixmap)
            painter.setOpacity(0.8)
            widget.render(painter, QPoint(0, 0))
            painter.end()
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        drag.exec(Qt.DropAction.MoveAction)

        self._drag_start_pos = None
        self._dragged_item = None
        self._drop_indicator_index = -1
        self._merge_target_index = -1
        self.update()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat("application/x-layer-index"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if not event.mimeData().hasFormat("application/x-layer-index"):
            event.ignore()
            return

        event.acceptProposedAction()

        pos = event.pos()
        item = self.itemAt(pos)
        source_row = int(event.mimeData().data("application/x-layer-index").data().decode())

        if item:
            target_row = self.row(item)
            item_rect = self.visualItemRect(item)
            mid_y = item_rect.center().y()

            if target_row == source_row:
                self._drop_indicator_index = -1
                self._merge_target_index = -1
            elif abs(pos.y() - mid_y) < item_rect.height() // 4:
                self._drop_indicator_index = -1
                self._merge_target_index = target_row
            else:
                self._merge_target_index = -1
                if pos.y() < mid_y:
                    self._drop_indicator_index = target_row
                else:
                    self._drop_indicator_index = target_row + 1
        else:
            self._drop_indicator_index = self.count()
            self._merge_target_index = -1

        self.update()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._drop_indicator_index = -1
        self._merge_target_index = -1
        self.update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        if not event.mimeData().hasFormat("application/x-layer-index"):
            event.ignore()
            return

        source_row = int(event.mimeData().data("application/x-layer-index").data().decode())

        if self._merge_target_index >= 0 and self._merge_target_index != source_row:
            self.layers_merge_requested.emit(source_row, self._merge_target_index)
            event.acceptProposedAction()
        elif self._drop_indicator_index >= 0:
            target_row = self._drop_indicator_index
            if target_row > source_row:
                target_row -= 1

            if target_row != source_row:
                self.layers_reordered.emit(source_row, target_row)
            event.acceptProposedAction()
        else:
            event.ignore()

        self._drop_indicator_index = -1
        self._merge_target_index = -1
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)

        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._drop_indicator_index >= 0:
            if self._drop_indicator_index < self.count():
                item = self.item(self._drop_indicator_index)
                if item:
                    rect = self.visualItemRect(item)
                    y = rect.top()
                else:
                    y = 10
            else:
                if self.count() > 0:
                    item = self.item(self.count() - 1)
                    if item:
                        rect = self.visualItemRect(item)
                        y = rect.bottom()
                    else:
                        y = 10
                else:
                    y = 10

            painter.setPen(QPen(QColor(THEME.accent_primary), 3))
            painter.drawLine(10, y, self.viewport().width() - 10, y)

            painter.setBrush(QColor(THEME.accent_primary))
            painter.drawEllipse(QPoint(10, y), 4, 4)
            painter.drawEllipse(QPoint(self.viewport().width() - 10, y), 4, 4)

        if self._merge_target_index >= 0 and self._merge_target_index < self.count():
            item = self.item(self._merge_target_index)
            if item:
                rect = self.visualItemRect(item)

                painter.setPen(QPen(QColor(THEME.accent_secondary), 3))
                highlight = QColor(THEME.accent_secondary)
                highlight.setAlpha(64)
                painter.setBrush(highlight)
                painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)

                painter.setPen(QColor(THEME.accent_secondary))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "⊕ " + t("Zusammenführen"))


class LayerPanel(QWidget):
    """Panel zur Verwaltung von Layern mit Drag & Drop."""

    layer_selected = Signal(int)
    layers_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layer_stack: LayerStack | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Hinweis
        self.hint_label = QLabel("💡 " + t("Ziehen zum Verschieben, auf Ebene ziehen zum Vereinen"))
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet(f"""
            color: {THEME.text_muted};
            font-size: 10px;
            background: {THEME.bg_light};
            border-radius: 4px;
            padding: 6px;
        """)
        layout.addWidget(self.hint_label)

        # Layer-Liste
        self.list_widget = DraggableLayerList()
        self.list_widget.setSpacing(2)
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.list_widget.layers_reordered.connect(self._on_layers_reordered)
        self.list_widget.layers_merge_requested.connect(self._on_layers_merge_requested)
        layout.addWidget(self.list_widget, 1)

        # Opacity
        opacity_frame = QFrame()
        opacity_frame.setStyleSheet("background: transparent;")
        opacity_layout = QHBoxLayout(opacity_frame)
        opacity_layout.setContentsMargins(0, 4, 0, 4)
        opacity_layout.setSpacing(6)

        self.opacity_label = QLabel(t("Deckkraft"))
        self.opacity_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 10px;")
        opacity_layout.addWidget(self.opacity_label)

        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.setValue(100)
        self.slider_opacity.valueChanged.connect(self._on_opacity_changed)
        opacity_layout.addWidget(self.slider_opacity)

        self.lbl_opacity = QLabel("100%")
        self.lbl_opacity.setFixedWidth(36)
        self.lbl_opacity.setStyleSheet(
            f"color: {THEME.accent_primary}; font-size: 10px; font-weight: 600;"
        )
        opacity_layout.addWidget(self.lbl_opacity)

        layout.addWidget(opacity_frame)

        # Notiz-Feld zur aktuellen Ebene
        self.lbl_note = QLabel("📝  " + t("Notiz zur Ebene"))
        self.lbl_note.setStyleSheet(
            f"color: {THEME.text_secondary}; font-size: 11px; font-weight: 600; "
            f"padding: 4px 0 2px 0;"
        )
        layout.addWidget(self.lbl_note)

        self.edit_note = QPlainTextEdit()
        self.edit_note.setPlaceholderText(t("z.B. Vordergrund, Schatten, Backstitch-Linien …"))
        self.edit_note.setToolTip(
            t(
                "Freie Notiz zur aktuell ausgewaehlten Ebene — wird beim "
                "Speichern in der .pxs-Datei abgelegt."
            )
        )
        self.edit_note.setFixedHeight(60)
        self.edit_note.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._apply_note_style()
        # focusOut → committen, damit der Layer-Note in Pattern landet
        self.edit_note.focusOutEvent = self._wrap_note_focus_out(self.edit_note.focusOutEvent)
        layout.addWidget(self.edit_note)

        # Button-Zeile
        btn_frame = QFrame()
        btn_frame.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 4, 0, 0)
        btn_layout.setSpacing(3)

        btn_style = self._get_btn_style()

        self.btn_add = QPushButton("+")
        self.btn_add.setFixedSize(28, 26)
        self.btn_add.setToolTip(t("Neue Ebene"))
        self.btn_add.setStyleSheet(btn_style)
        self.btn_add.clicked.connect(self._on_add_layer)
        btn_layout.addWidget(self.btn_add)

        self.btn_remove = QPushButton("−")
        self.btn_remove.setFixedSize(28, 26)
        self.btn_remove.setToolTip(t("Löschen"))
        self.btn_remove.setStyleSheet(btn_style)
        self.btn_remove.clicked.connect(self._on_remove_layer)
        btn_layout.addWidget(self.btn_remove)

        self.btn_duplicate = QPushButton("⊕")
        self.btn_duplicate.setFixedSize(28, 26)
        self.btn_duplicate.setToolTip(t("Duplizieren"))
        self.btn_duplicate.setStyleSheet(btn_style)
        self.btn_duplicate.clicked.connect(self._on_duplicate_layer)
        btn_layout.addWidget(self.btn_duplicate)

        btn_layout.addStretch()
        layout.addWidget(btn_frame)

        self.setMinimumWidth(220)
        self.setMaximumWidth(280)

    def _apply_theme(self) -> None:
        """Re-applies all stylesheets for theme switching."""
        self.hint_label.setStyleSheet(f"""
            color: {THEME.text_muted};
            font-size: 10px;
            background: {THEME.bg_light};
            border-radius: 4px;
            padding: 6px;
        """)
        self.list_widget._apply_theme()
        self.opacity_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 10px;")
        self.lbl_opacity.setStyleSheet(
            f"color: {THEME.accent_primary}; font-size: 10px; font-weight: 600;"
        )
        self.lbl_note.setStyleSheet(
            f"color: {THEME.text_secondary}; font-size: 11px; font-weight: 600; "
            f"padding: 4px 0 2px 0;"
        )
        self._apply_note_style()
        btn_style = self._get_btn_style()
        self.btn_add.setStyleSheet(btn_style)
        self.btn_remove.setStyleSheet(btn_style)
        self.btn_duplicate.setStyleSheet(btn_style)
        # Refresh item widgets
        self._refresh_list()

    def _get_btn_style(self) -> str:
        # padding explizit auf 0: die globale App-QSS setzt fuer QPushButton
        # "padding: 6px 16px; min-height: 22px;" (siehe apply_theme_to_app).
        # Diese Werte werden hier NICHT automatisch durch das Fehlen einer
        # eigenen Angabe ausser Kraft gesetzt — Qt merged ungesetzte
        # Properties aus der App-weiten Stylesheet rein. Bei
        # setFixedSize(28, 26) blieb dadurch kein Platz mehr fuer das Glyph
        # (16px Padding pro Seite > 28px Breite) — die Buttons wirkten
        # komplett leer.
        # WICHTIG: min-width/min-height NICHT hier auf 0 setzen — ein in
        # der QSS gesetztes min-width/min-height ueberschreibt Qts intern
        # via setFixedSize() gesetzte minimumSize/maximumSize, wodurch der
        # Button auf seine Inhaltsgroesse zusammenschrumpft statt bei den
        # fixen 28x26px zu bleiben.
        return f"""
            QPushButton {{
                background: {THEME.bg_light};
                border: 1px solid {THEME.border_light};
                border-radius: 3px;
                padding: 0;
                font-size: 12px;
                font-weight: bold;
                color: {THEME.text_secondary};
            }}
            QPushButton:hover {{
                background: {THEME.bg_lighter};
                border-color: {THEME.accent_primary};
                color: {THEME.text_primary};
            }}
            QPushButton:pressed {{
                background: {THEME.accent_primary};
                color: {THEME.bg_dark};
            }}
        """

    def set_layer_stack(self, layer_stack: LayerStack) -> None:
        """Setzt den Layer-Stack und aktualisiert die Anzeige."""
        self._layer_stack = layer_stack
        self._refresh_list()

    def _refresh_list(self) -> None:
        """Aktualisiert die Layer-Liste."""
        self.list_widget.clear()

        if not self._layer_stack:
            return

        for i in range(len(self._layer_stack) - 1, -1, -1):
            layer = self._layer_stack[i]

            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, i)

            widget = LayerListItem(layer, i)
            widget.visibility_changed.connect(self._on_layer_property_changed)
            widget.lock_changed.connect(self._on_layer_property_changed)

            item.setSizeHint(QSize(200, 46))
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

        active_idx = self._layer_stack.active_index
        display_idx = len(self._layer_stack) - 1 - active_idx
        if 0 <= display_idx < self.list_widget.count():
            self.list_widget.setCurrentRow(display_idx)

    def _get_actual_index(self, display_index: int) -> int:
        """Konvertiert Display-Index zu tatsächlichem Layer-Index."""
        if not self._layer_stack:
            return -1
        return len(self._layer_stack) - 1 - display_index

    def _on_layers_reordered(self, from_display: int, to_display: int) -> None:
        """Handler für Layer-Neuordnung per Drag & Drop."""
        if not self._layer_stack:
            return

        from_actual = self._get_actual_index(from_display)
        to_actual = self._get_actual_index(to_display)

        if self._layer_stack.move_layer_to(from_actual, to_actual):
            self._refresh_list()
            self.layers_changed.emit()

    def _on_layers_merge_requested(self, source_display: int, target_display: int) -> None:
        """Handler für Layer-Zusammenführung per Drag & Drop."""
        if not self._layer_stack:
            return

        source_actual = self._get_actual_index(source_display)
        target_actual = self._get_actual_index(target_display)

        source_layer = self._layer_stack[source_actual]
        target_layer = self._layer_stack[target_actual]

        if source_layer.locked or target_layer.locked:
            QMessageBox.warning(
                self,
                t("Ebenen vereinen"),
                t(
                    "Gesperrte Ebenen können nicht vereint werden.\n\nBitte entsperre zuerst die betroffene(n) Ebene(n)."
                ),
            )
            return

        reply = QMessageBox.question(
            self,
            t("Ebenen vereinen"),
            f"'{source_layer.name}' mit '{target_layer.name}' vereinen?\n\n"
            f"Die Stiche von '{source_layer.name}' werden auf '{target_layer.name}' übertragen.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self._layer_stack.merge_layers(source_actual, target_actual):
                self._refresh_list()
                self.layers_changed.emit()

    def _on_selection_changed(self, display_index: int) -> None:
        """Handler für Auswahländerung in der Layer-Liste."""
        # Vor dem Wechsel die offene Notiz committen, damit sie nicht verloren geht
        self._commit_note()
        actual_index = self._get_actual_index(display_index)
        if self._layer_stack and actual_index >= 0:
            self._layer_stack.active_index = actual_index
            layer = self._layer_stack.active_layer
            if layer:
                self.slider_opacity.setValue(int(layer.opacity * 100))
                # Notiz ohne Signal aktualisieren — sonst triggert das focusOut
                self.edit_note.blockSignals(True)
                self.edit_note.setPlainText(layer.note)
                self.edit_note.blockSignals(False)
            self.layer_selected.emit(actual_index)

    def _apply_note_style(self) -> None:
        """Style fuer Notiz-Editor — kontrastreich, klar als Eingabefeld erkennbar."""
        self.edit_note.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {THEME.bg_light};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_light};
                border-radius: 4px;
                padding: 4px 6px;
                font-size: 11px;
            }}
            QPlainTextEdit:focus {{
                border: 1px solid {THEME.accent_primary};
                background: {THEME.bg_lighter};
            }}
        """)
        # Placeholder-Farbe via Palette (CSS-Property fuer Placeholder-Color
        # ist nicht ueberall stabil unterstuetzt). text_muted hebt sich klar
        # vom bg_light ab, ohne mit echtem Inhalt verwechselt zu werden.
        pal = self.edit_note.palette()
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(THEME.text_muted))
        self.edit_note.setPalette(pal)

    def _wrap_note_focus_out(self, original):
        """Dekoriert focusOutEvent, sodass beim Verlassen die Notiz committet wird."""

        def wrapped(event):
            self._commit_note()
            original(event)

        return wrapped

    def _commit_note(self) -> None:
        """Schreibt den aktuellen Notiz-Text in den aktiven Layer (falls geaendert)."""
        if not self._layer_stack:
            return
        layer = self._layer_stack.active_layer
        if layer is None:
            return
        new_text = self.edit_note.toPlainText()
        if new_text != layer.note:
            layer.note = new_text
            self.layers_changed.emit()

    def _on_opacity_changed(self, value: int) -> None:
        """Handler für Deckkraft-Änderung."""
        self.lbl_opacity.setText(f"{value}%")
        if self._layer_stack and self._layer_stack.active_layer:
            self._layer_stack.active_layer.opacity = value / 100.0
            self.layers_changed.emit()

    def _on_layer_property_changed(self) -> None:
        """Handler für Änderungen an Layer-Eigenschaften."""
        self.layers_changed.emit()

    def _on_add_layer(self) -> None:
        """Fügt eine neue Ebene hinzu."""
        if not self._layer_stack:
            return
        name, ok = QInputDialog.getText(
            self, t("Neue Ebene"), t("Name:"), text=f"{t('Ebene')} {len(self._layer_stack) + 1}"
        )
        if ok and name:
            self._layer_stack.add_layer(name)
            self._refresh_list()
            self.layers_changed.emit()

    def _on_remove_layer(self) -> None:
        """Entfernt die ausgewählte Ebene."""
        if not self._layer_stack or len(self._layer_stack) <= 1:
            QMessageBox.warning(self, t("Hinweis"), t("Mindestens eine Ebene erforderlich."))
            return

        display_idx = self.list_widget.currentRow()
        actual_idx = self._get_actual_index(display_idx)
        layer = self._layer_stack[actual_idx]

        reply = QMessageBox.question(
            self,
            t("Ebene löschen"),
            f"'{layer.name}' löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._layer_stack.remove_layer(actual_idx)
            self._refresh_list()
            self.layers_changed.emit()

    def _on_duplicate_layer(self) -> None:
        """Dupliziert die ausgewählte Ebene."""
        if not self._layer_stack:
            return
        display_idx = self.list_widget.currentRow()
        actual_idx = self._get_actual_index(display_idx)
        self._layer_stack.duplicate_layer(actual_idx)
        self._refresh_list()
        self.layers_changed.emit()

    def _show_context_menu(self, pos: QPoint) -> None:
        """Zeigt das Kontextmenü für die Layer-Liste."""
        item = self.list_widget.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)
        menu.addAction(t("Umbenennen"), self._on_rename_layer)
        menu.addSeparator()
        menu.addAction(t("Duplizieren"), self._on_duplicate_layer)
        menu.addAction(t("Löschen"), self._on_remove_layer)
        menu.addSeparator()
        menu.addAction(t("Leeren"), self._on_clear_layer)
        menu.exec(self.list_widget.mapToGlobal(pos))

    def _on_rename_layer(self) -> None:
        """Benennt die ausgewählte Ebene um."""
        if not self._layer_stack:
            return
        display_idx = self.list_widget.currentRow()
        actual_idx = self._get_actual_index(display_idx)
        layer = self._layer_stack[actual_idx]
        name, ok = QInputDialog.getText(self, t("Umbenennen"), t("Name:"), text=layer.name)
        if ok and name:
            layer.name = name
            self._refresh_list()

    def _on_clear_layer(self) -> None:
        """Leert die ausgewählte Ebene."""
        if not self._layer_stack:
            return
        display_idx = self.list_widget.currentRow()
        actual_idx = self._get_actual_index(display_idx)
        layer = self._layer_stack[actual_idx]
        reply = QMessageBox.question(
            self,
            t("Ebene leeren"),
            f"Alle Stiche aus '{layer.name}' entfernen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            layer.clear()
            self._refresh_list()
            self.layers_changed.emit()
