"""
Muster-Vorschau & Simulations-Dialog.

Bietet drei Darstellungsmodi:
- Stoff-Vorschau (realistisch mit Fadentextur)
- Pixel-Vorschau (flache Farben)
- Symbol-Plan (schwarz-weiß mit Gitternetz)

Features:
- Interaktives Zoomen (Mausrad + Slider)
- Panning per Drag
- Stoff- und Farbauswahl
- Bild-Export in konfigurierbarer Auflösung
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QWheelEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ...config import UI_CONFIG
from ...core.constants import (
    COMMON_FABRIC_COUNTS,
    DEFAULT_FABRIC_COUNT,
    DEFAULT_ZOOM_PERCENT,
    MAX_ZOOM_PERCENT,
    MIN_ZOOM_PERCENT,
)
from ..rendering import PreviewRenderEngine, RenderMode
from ..styles import THEME

if TYPE_CHECKING:
    from ...core import Pattern


# =============================================================================
# PreviewCanvas — Interaktives Vorschau-Widget
# =============================================================================


class PreviewCanvas(QWidget):
    """
    Interaktives Canvas-Widget für die Muster-Vorschau.

    Unterstützt Zoom per Mausrad und Pan per Drag.
    """

    zoom_changed = Signal(int)  # Zoom-Prozent

    MIN_ZOOM = MIN_ZOOM_PERCENT
    MAX_ZOOM = MAX_ZOOM_PERCENT
    PREVIEW_CELL_SIZE = 10  # Basis-Zellgröße bei 100% in der Vorschau

    def __init__(self, engine: PreviewRenderEngine, pattern: "Pattern", parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._pattern = pattern

        self._zoom_percent = DEFAULT_ZOOM_PERCENT
        self._pan_offset = QPointF(0, 0)

        self._dragging = False
        self._drag_start = QPointF()
        self._drag_pan_start = QPointF()

        self.setMinimumSize(300, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # Kein Default-Kontextmenu (Qt feuert sonst beim Rechtsklick-Drag
        # einen Toggle, der visuell flackert)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setStyleSheet(f"background: {THEME.bg_dark};")

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def cell_size(self) -> int:
        """Aktuelle Zellgröße in Pixeln."""
        return max(2, int(self.PREVIEW_CELL_SIZE * self._zoom_percent / 100))

    @property
    def pattern_pixel_width(self) -> int:
        return self._pattern.width * self.cell_size

    @property
    def pattern_pixel_height(self) -> int:
        return self._pattern.height * self.cell_size

    # =========================================================================
    # Zoom
    # =========================================================================

    def set_zoom(self, percent: int) -> None:
        """Setzt den Zoom-Level (25-400%)."""
        percent = max(self.MIN_ZOOM, min(self.MAX_ZOOM, percent))
        if percent != self._zoom_percent:
            self._zoom_percent = percent
            self.zoom_changed.emit(percent)
            self.update()

    def zoom_fit(self) -> None:
        """Passt den Zoom so an, dass das Muster komplett sichtbar ist."""
        if self._pattern.width <= 0 or self._pattern.height <= 0:
            return

        margin = 20
        available_w = self.width() - margin * 2
        available_h = self.height() - margin * 2

        if available_w <= 0 or available_h <= 0:
            return

        zoom_w = (available_w / self._pattern.width) / self.PREVIEW_CELL_SIZE * 100
        zoom_h = (available_h / self._pattern.height) / self.PREVIEW_CELL_SIZE * 100
        zoom = int(min(zoom_w, zoom_h))
        zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, zoom))

        self._zoom_percent = zoom
        # Zentrieren
        self._pan_offset = QPointF(
            (self.width() - self.pattern_pixel_width) / 2,
            (self.height() - self.pattern_pixel_height) / 2,
        )
        self.zoom_changed.emit(zoom)
        self.update()

    def zoom_100(self) -> None:
        """Setzt auf 100% und zentriert."""
        self._zoom_percent = DEFAULT_ZOOM_PERCENT
        self._pan_offset = QPointF(
            (self.width() - self.pattern_pixel_width) / 2,
            (self.height() - self.pattern_pixel_height) / 2,
        )
        self.zoom_changed.emit(DEFAULT_ZOOM_PERCENT)
        self.update()

    # =========================================================================
    # Painting
    # =========================================================================

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(THEME.bg_dark))

        if self._pattern.width <= 0 or self._pattern.height <= 0:
            painter.setPen(QColor(THEME.text_muted))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Kein Muster geladen")
            return

        cs = self.cell_size
        pan_x = self._pan_offset.x()
        pan_y = self._pan_offset.y()

        # Viewport in Pattern-Pixel-Koordinaten
        vp_x = max(0, int(-pan_x))
        vp_y = max(0, int(-pan_y))
        vp_w = min(self._pattern.width * cs - vp_x, self.width())
        vp_h = min(self._pattern.height * cs - vp_y, self.height())

        if vp_w <= 0 or vp_h <= 0:
            return

        viewport = QRectF(vp_x, vp_y, vp_w, vp_h).toAlignedRect()
        image = self._engine.render(cs, viewport)

        # Position im Widget
        cell_range = getattr(image, "_cell_range", (0, 0, 0, 0))
        x_start, y_start = cell_range[0], cell_range[1]

        target_x = pan_x + x_start * cs
        target_y = pan_y + y_start * cs

        painter.drawImage(int(target_x), int(target_y), image)

        # Rahmen um das Muster
        painter.setPen(QColor(THEME.border_light))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(
            int(pan_x) - 1,
            int(pan_y) - 1,
            self.pattern_pixel_width + 1,
            self.pattern_pixel_height + 1,
        )

    # =========================================================================
    # Maus-Events
    # =========================================================================

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom per Mausrad, zentriert auf Mausposition.

        Zoom-Schritt: multiplikativ (15% pro Tick) MIT absolutem Mindest-
        Schritt von 5 Prozentpunkten. Sonst waere der Zoom im kleinen
        Bereich traege (20% → 23% → 26% bei reinem *1.15). Plus: angleDelta
        wird durch 120 (Standard-Tick) geteilt, damit schnelle Wheel-Bursts
        oder Touchpad-Pinch (kontinuierliche Werte) mehrere Stufen auf
        einmal anwenden — Strg+Wheel zoomt feiner (nur multiplikativ).
        """
        old_zoom = self._zoom_percent
        old_cs = self.cell_size

        from PySide6.QtCore import Qt

        fine = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        # Tick-Anzahl: jeder Standard-Maus-Tick = 120. Bei Touchpads oder
        # schnellem Scrollen koennen mehrere Ticks aufsummiert ankommen.
        ticks = max(1, abs(event.angleDelta().y()) // 120)
        delta = event.angleDelta().y()
        if delta == 0:
            return

        # Min-Step: 5 Prozentpunkte pro Tick (Default), bei Strg+Wheel 2.
        min_step = 2 if fine else 5
        new_zoom = old_zoom
        for _ in range(ticks):
            if delta > 0:
                step = max(min_step, int(new_zoom * 0.15))
                new_zoom = min(self.MAX_ZOOM, new_zoom + step)
            else:
                step = max(min_step, int(new_zoom * 0.15 / 1.15))
                new_zoom = max(self.MIN_ZOOM, new_zoom - step)

        if new_zoom == old_zoom:
            return

        # Zoom um Mausposition
        mouse_pos = event.position()
        # Pattern-Koordinate unter Maus
        grid_x = (mouse_pos.x() - self._pan_offset.x()) / old_cs
        grid_y = (mouse_pos.y() - self._pan_offset.y()) / old_cs

        self._zoom_percent = new_zoom
        new_cs = self.cell_size

        # Neuen Offset berechnen damit gleiche Pattern-Position unter Maus bleibt
        self._pan_offset = QPointF(
            mouse_pos.x() - grid_x * new_cs,
            mouse_pos.y() - grid_y * new_cs,
        )

        self.zoom_changed.emit(new_zoom)
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        # WICHTIG: event.accept() bei Middle-Klick verhindert Windows
        # AutoScroll-Modus (das flackernde "Scrollen deaktiviert"-Toast).
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton):
            self._dragging = True
            self._drag_start = event.position()
            self._drag_pan_start = QPointF(self._pan_offset)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            delta = event.position() - self._drag_start
            self._pan_offset = self._drag_pan_start + delta
            self.update()
            event.accept()
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self._dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()

    def resizeEvent(self, event) -> None:
        """Bei Größenänderung: Vorschau neu zentrieren wenn zoom_fit aktiv."""
        super().resizeEvent(event)


# =============================================================================
# PatternPreviewDialog — Hauptdialog
# =============================================================================


class PatternPreviewDialog(QDialog):
    """
    Dialog für Muster-Vorschau und Simulation.

    Bietet realistische Stoff-Vorschau, Pixel-Vorschau und Symbol-Plan
    mit interaktivem Zoom/Pan und Bild-Export.
    """

    def __init__(self, pattern: "Pattern", parent=None) -> None:
        super().__init__(parent)
        self._pattern = pattern
        self._is_dp = getattr(pattern, "mode", "stitch") == "diamond"

        self._engine = PreviewRenderEngine(pattern)

        title_suffix = "Vorlagen-Vorschau" if self._is_dp else "Muster-Vorschau"
        self.setWindowTitle(f"{title_suffix} — {pattern.name}")
        self.setMinimumSize(*UI_CONFIG.dialog_min_large)
        self.resize(1100, 800)

        self._setup_ui()
        self._apply_styles()
        self._update_info()
        # Initial-Beschreibung fuer den Default-Modus
        initial_descs = self.DP_MODE_DESCRIPTIONS if self._is_dp else self.MODE_DESCRIPTIONS
        self._mode_desc.setText(initial_descs[0])

        # Initial: Einpassen
        from PySide6.QtCore import QTimer

        QTimer.singleShot(50, self._canvas.zoom_fit)

    # =========================================================================
    # UI-Setup
    # =========================================================================

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 12, 14, 12)

        # --- Erklärungs-Banner (modus-spezifisch) ---
        if self._is_dp:
            intro_text = (
                "So sieht deine Vorlage fertig geklebt aus. Die Drills haben "
                "die typische Glanz-Optik mit hellerer Oberseite und "
                "dunklerem Schatten. Mit dem Mausrad zoomst du, mit Drag "
                "verschiebst du die Ansicht."
            )
        else:
            intro_text = (
                "So sieht dein Muster gestickt aus. Wechsle den <b>Modus</b> für "
                "verschiedene Darstellungen, probiere unterschiedliche <b>Stoffe</b> "
                "und <b>Stoff-Farben</b>. Mit dem Mausrad zoomst du, mit Drag "
                "verschiebst du die Ansicht."
            )
        intro = QLabel(intro_text)
        intro.setWordWrap(True)
        intro.setStyleSheet(
            f"color: {THEME.text_secondary}; font-size: 12px; "
            f"background: {THEME.bg_light}; border-left: 3px solid {THEME.accent_primary}; "
            f"border-radius: 6px; padding: 8px 12px;"
        )
        layout.addWidget(intro)

        # --- Toolbar (jetzt in zwei logische Reihen aufgeteilt) ---
        toolbar = self._create_toolbar()
        layout.addLayout(toolbar)

        # --- Mode-Beschreibung ---
        self._mode_desc = QLabel("")
        self._mode_desc.setStyleSheet(
            f"color: {THEME.text_muted}; font-size: 10px; font-style: italic; "
            f"padding: 0 2px 4px 2px;"
        )
        layout.addWidget(self._mode_desc)

        # --- Canvas ---
        self._canvas = PreviewCanvas(self._engine, self._pattern, self)
        self._canvas.zoom_changed.connect(self._on_canvas_zoom_changed)
        layout.addWidget(self._canvas, 1)

        # --- Info-Bar ---
        info_bar = self._create_info_bar()
        layout.addLayout(info_bar)

        # --- Footer ---
        footer = self._create_footer()
        layout.addLayout(footer)

    def _create_toolbar(self) -> QHBoxLayout:
        """Erstellt die Toolbar — gruppiert Darstellung / Stoff / Optionen / Zoom.

        Im DP-Modus werden die irrelevanten Gruppen (Stoff, Rueckstiche,
        Fortschritt) komplett ausgeblendet — die Vorschau zeigt dort
        nur die Drill-Optik mit Klebegrund.
        """
        row = QHBoxLayout()
        row.setSpacing(12)

        # === Gruppe: Modus (Darstellung) ===
        self._mode_label_widget = self._make_group_label(
            "Drill-Darstellung" if self._is_dp else "Darstellung"
        )
        row.addWidget(self._mode_label_widget)
        self._mode_combo = QComboBox()
        if self._is_dp:
            # Im DP-Modus gibt's keinen "Stoff" und keinen "Symbol-Plan"
            # — wir bieten zwei realistische DP-Renderings an.
            self._mode_combo.addItems(["Drill-Vorschau", "Pixel-Vorschau"])
            self._mode_combo.setToolTip(
                "Drill-Vorschau: facettierte Drills auf Klebegrund.\n"
                "Pixel-Vorschau: flache Farbflaechen — wie im Editor."
            )
        else:
            self._mode_combo.addItems(["Stoff-Vorschau", "Pixel-Vorschau", "Symbol-Plan"])
            self._mode_combo.setToolTip(
                "Stoff-Vorschau: realistisch mit Aida-Textur und Kreuzstich-Muster.\n"
                "Pixel-Vorschau: flache Farbflächen — wie das Pattern im Editor.\n"
                "Symbol-Plan: schwarz-weiße Symbole — zum Drucken."
            )
        self._mode_combo.setMinimumWidth(160)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        row.addWidget(self._mode_combo)

        # Separator zwischen Modus und Stoff — im DP-Modus ausgeblendet.
        self._sep_after_mode = self._make_separator()
        row.addWidget(self._sep_after_mode)

        # === Gruppe: Stoff (nur im Stick-Modus relevant) ===
        self._fabric_group_label = self._make_group_label("Stoff")
        row.addWidget(self._fabric_group_label)
        self._fabric_combo = QComboBox()
        self._fabric_combo.addItems(
            ["Aida 11", "Aida 14", "Aida 16", "Aida 18", "Evenweave 28", "Leinen 32"]
        )
        self._fabric_combo.setCurrentIndex(1)  # Aida 14
        self._fabric_combo.setMinimumWidth(110)
        self._fabric_combo.setToolTip(
            "Stoffart — höhere Zahl = feiner gewebt = kleineres fertiges Muster"
        )
        self._fabric_combo.currentIndexChanged.connect(self._on_fabric_changed)
        row.addWidget(self._fabric_combo)

        self._color_combo = QComboBox()
        self._color_combo.addItems(list(PreviewRenderEngine.FABRIC_COLORS.keys()))
        self._color_combo.setMinimumWidth(110)
        self._color_combo.setToolTip("Farbe des Stoff-Hintergrunds")
        self._color_combo.currentTextChanged.connect(self._on_color_changed)
        row.addWidget(self._color_combo)

        self._sep_after_fabric = self._make_separator()
        row.addWidget(self._sep_after_fabric)

        # === Gruppe: Optionen (Rueckstiche / Fortschritt — beide weg im DP) ===
        self._cb_backstitches = QCheckBox("Rückstiche")
        self._cb_backstitches.setChecked(True)
        self._cb_backstitches.setToolTip("Rückstich-Linien in der Vorschau zeigen")
        self._cb_backstitches.toggled.connect(self._on_toggle_backstitches)
        row.addWidget(self._cb_backstitches)

        self._cb_completion = QCheckBox("Fortschritt")
        self._cb_completion.setChecked(False)
        self._cb_completion.setToolTip("Bereits erledigte Stiche markieren")
        self._cb_completion.toggled.connect(self._on_toggle_completion)
        row.addWidget(self._cb_completion)

        # Im DP-Modus alle Stick-spezifischen Widgets verstecken.
        if self._is_dp:
            for w in (
                self._fabric_group_label,
                self._fabric_combo,
                self._color_combo,
                self._sep_after_fabric,
                self._cb_backstitches,
                self._cb_completion,
            ):
                w.setVisible(False)

        row.addStretch()

        # === Gruppe: Zoom ===
        row.addWidget(self._make_group_label("Zoom"))
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(PreviewCanvas.MIN_ZOOM, PreviewCanvas.MAX_ZOOM)
        self._zoom_slider.setValue(DEFAULT_ZOOM_PERCENT)
        self._zoom_slider.setFixedWidth(140)
        self._zoom_slider.setToolTip("Zoom — auch per Mausrad im Vorschau-Bereich möglich")
        self._zoom_slider.valueChanged.connect(self._on_slider_zoom_changed)
        row.addWidget(self._zoom_slider)

        self._zoom_label = QLabel(f"{DEFAULT_ZOOM_PERCENT}%")
        self._zoom_label.setFixedWidth(50)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_label.setStyleSheet(
            f"color: {THEME.accent_primary}; font-weight: 600; font-size: 11px;"
        )
        row.addWidget(self._zoom_label)

        btn_fit = QPushButton("Einpassen")
        btn_fit.setMinimumWidth(96)
        btn_fit.setToolTip("Zoom so anpassen, dass das ganze Muster sichtbar ist")
        btn_fit.clicked.connect(lambda: self._canvas.zoom_fit())
        row.addWidget(btn_fit)

        btn_100 = QPushButton("1:1")
        btn_100.setMinimumWidth(46)
        btn_100.setToolTip("Auf 100% Zoom setzen")
        btn_100.clicked.connect(lambda: self._canvas.zoom_100())
        row.addWidget(btn_100)

        return row

    def _make_group_label(self, text: str) -> QLabel:
        """Mini-Label für Toolbar-Gruppen."""
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {THEME.text_muted}; font-size: 10px; "
            f"font-weight: 700; letter-spacing: 1px; padding-right: 2px;"
        )
        return lbl

    def _make_separator(self) -> QFrame:
        """Vertikaler Trenner für die Toolbar."""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {THEME.border_medium}; max-width: 1px;")
        return sep

    def _create_info_bar(self) -> QHBoxLayout:
        """Erstellt die Info-Leiste am unteren Rand."""
        info = QHBoxLayout()
        info.setSpacing(20)

        style = f"color: {THEME.text_muted}; font-size: 11px;"

        self._label_size = QLabel("-- × -- cm")
        self._label_size.setStyleSheet(style)
        info.addWidget(self._label_size)

        sep1 = QLabel("|")
        sep1.setStyleSheet(f"color: {THEME.border_dark};")
        info.addWidget(sep1)

        self._label_stitches = QLabel("-- Stiche")
        self._label_stitches.setStyleSheet(style)
        info.addWidget(self._label_stitches)

        sep2 = QLabel("|")
        sep2.setStyleSheet(f"color: {THEME.border_dark};")
        info.addWidget(sep2)

        self._label_colors = QLabel("-- Farben")
        self._label_colors.setStyleSheet(style)
        info.addWidget(self._label_colors)

        sep3 = QLabel("|")
        sep3.setStyleSheet(f"color: {THEME.border_dark};")
        info.addWidget(sep3)

        self._label_progress = QLabel("-- %")
        self._label_progress.setStyleSheet(style)
        info.addWidget(self._label_progress)

        # Fortschritts-Label + Separator im DP-Modus ausblenden
        # (DP hat keinen "Stich abhaken"-Workflow).
        if self._is_dp:
            sep3.setVisible(False)
            self._label_progress.setVisible(False)

        info.addStretch()

        return info

    def _create_footer(self) -> QHBoxLayout:
        """Erstellt den Footer mit Export- und Schließen-Buttons."""
        footer = QHBoxLayout()

        export_btn = QPushButton("📷 Als Bild speichern...")
        export_btn.clicked.connect(self._on_export_image)
        footer.addWidget(export_btn)

        footer.addStretch()

        close_btn = QPushButton("Schließen")
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {THEME.accent_primary};
                color: {THEME.bg_dark};
                font-weight: bold;
                padding: 8px 20px;
            }}
        """)
        footer.addWidget(close_btn)

        return footer

    # =========================================================================
    # Styling
    # =========================================================================

    def _apply_styles(self) -> None:
        # Konsistent mit Settings/Harmony-Dialog: bessere Inputs + Akzent-Slider
        self.setStyleSheet(f"""
            QDialog {{
                background: {THEME.bg_dark};
            }}
            QLabel {{
                color: {THEME.text_primary};
                background: transparent;
            }}
            QComboBox {{
                background: {THEME.bg_dark};
                color: {THEME.text_primary};
                border: 2px solid {THEME.border_medium};
                border-radius: 6px;
                padding: 5px 10px;
                min-height: 26px;
            }}
            QComboBox:hover {{
                border-color: {THEME.accent_primary};
            }}
            QComboBox:disabled {{
                color: {THEME.text_disabled};
                background: {THEME.bg_medium};
                border-color: {THEME.border_dark};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 22px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {THEME.accent_primary};
            }}
            QCheckBox {{
                color: {THEME.text_primary};
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid {THEME.border_medium};
                background: {THEME.bg_dark};
            }}
            QCheckBox::indicator:hover {{
                border-color: {THEME.accent_primary};
            }}
            QCheckBox::indicator:checked {{
                background: {THEME.accent_primary};
                border-color: {THEME.accent_primary};
            }}
            QPushButton {{
                background: {THEME.bg_light};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_medium};
                border-radius: 6px;
                padding: 7px 14px;
                min-height: 26px;
            }}
            QPushButton:hover {{
                background: {THEME.bg_lighter};
                border-color: {THEME.accent_primary};
            }}
            QSlider::groove:horizontal {{
                background: {THEME.bg_lighter};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {THEME.accent_primary};
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {THEME.success};
            }}
            QSlider::sub-page:horizontal {{
                background: {THEME.accent_primary};
                border-radius: 3px;
            }}
        """)

    # =========================================================================
    # Event-Handler
    # =========================================================================

    MODE_DESCRIPTIONS = [
        "Realistische Vorschau mit Aida-Stoff-Textur und Kreuzstich-Symbolen — so sieht es im Stickrahmen aus.",
        "Pixel-Vorschau mit flachen Farben — schnell und klar wie im Editor.",
        "Schwarz-weißer Symbol-Plan — ideal zum Drucken und unterwegs benutzen.",
    ]

    DP_MODE_DESCRIPTIONS = [
        "Drill-Vorschau: facettierte Quadrate mit Glanzlicht und Schatten — so sieht die fertige DP-Vorlage geklebt aus.",
        "Pixel-Vorschau: flache Farbflaechen — schnell zur Kontroll-Ansicht ohne Drill-Detail.",
    ]

    def _on_mode_changed(self, index: int) -> None:
        """Wechselt den Darstellungsmodus.

        Im DP-Modus hat die Combo nur zwei Eintraege (Drill / Pixel) — der
        Renderer wechselt entsprechend zwischen FABRIC (mit DP-Drill-Render-
        Logik intern) und PIXEL.
        """
        if self._is_dp:
            modes = [RenderMode.FABRIC, RenderMode.PIXEL]
            descs = self.DP_MODE_DESCRIPTIONS
        else:
            modes = [RenderMode.FABRIC, RenderMode.PIXEL, RenderMode.SYMBOL]
            descs = self.MODE_DESCRIPTIONS

        if 0 <= index < len(modes):
            self._engine.set_render_mode(modes[index])

        # Bei Symbol-Plan im Stick-Modus: Stoff-Controls deaktivieren
        # (im DP-Modus sind die Controls ohnehin unsichtbar).
        if not self._is_dp:
            fabric_relevant = index != 2
            self._fabric_combo.setEnabled(fabric_relevant)
            self._color_combo.setEnabled(fabric_relevant)

        if 0 <= index < len(descs):
            self._mode_desc.setText(descs[index])

        self._canvas.update()

    def _on_fabric_changed(self, index: int) -> None:
        """Aktualisiert die Stoffart."""
        self._update_info()

    def _on_color_changed(self, color_name: str) -> None:
        """Aktualisiert die Stofffarbe."""
        color = PreviewRenderEngine.FABRIC_COLORS.get(color_name, QColor(255, 255, 255))
        self._engine.set_fabric_color(color)
        self._canvas.update()

    def _on_toggle_backstitches(self, checked: bool) -> None:
        self._engine.set_show_backstitches(checked)
        self._canvas.update()

    def _on_toggle_completion(self, checked: bool) -> None:
        self._engine.set_show_completion(checked)
        self._canvas.update()

    def _on_slider_zoom_changed(self, value: int) -> None:
        """Zoom-Slider wurde geändert."""
        self._zoom_label.setText(f"{value}%")
        self._canvas.set_zoom(value)

    def _on_canvas_zoom_changed(self, percent: int) -> None:
        """Canvas hat den Zoom geändert (per Mausrad)."""
        self._zoom_slider.blockSignals(True)
        self._zoom_slider.setValue(percent)
        self._zoom_slider.blockSignals(False)
        self._zoom_label.setText(f"{percent}%")

    # =========================================================================
    # Info & Export
    # =========================================================================

    def _update_info(self) -> None:
        """Aktualisiert die Info-Leiste."""
        stats = self._pattern.get_statistics()
        progress = self._pattern.get_progress_statistics()

        fabric_counts = COMMON_FABRIC_COUNTS
        idx = self._fabric_combo.currentIndex()
        count = fabric_counts[idx] if 0 <= idx < len(fabric_counts) else DEFAULT_FABRIC_COUNT
        stitches_per_cm = count / 2.54

        w_cm = self._pattern.width / stitches_per_cm
        h_cm = self._pattern.height / stitches_per_cm

        self._label_size.setText(f"{w_cm:.1f} × {h_cm:.1f} cm")
        unit_label = "Drills" if self._is_dp else "Stiche"
        self._label_stitches.setText(f"{stats['total_stitches']:,} {unit_label}")
        self._label_colors.setText(f"{stats['used_colors']} Farben")
        self._label_progress.setText(f"{progress['progress_percent']:.1f}%")

    def _on_export_image(self) -> None:
        """Exportiert die Vorschau als Bild."""
        # Auflösung wählen
        cell_size, ok = QInputDialog.getInt(
            self,
            "Auflösung",
            "Pixel pro Stich:",
            value=12,
            min=4,
            max=50,
        )
        if not ok:
            return

        # Warnung bei sehr großen Bildern
        total_px = self._pattern.width * cell_size * self._pattern.height * cell_size
        if total_px > 64_000_000:  # > 8000x8000 ~ 64 Megapixel
            reply = QMessageBox.question(
                self,
                "Großes Bild",
                f"Das Bild wird {self._pattern.width * cell_size} × "
                f"{self._pattern.height * cell_size} Pixel groß.\n"
                f"Fortfahren?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Datei-Dialog
        default_name = f"{self._pattern.name}_vorschau.png"
        path, _ = QFileDialog.getSaveFileName(
            self, "Als Bild speichern", default_name, "PNG (*.png);;JPEG (*.jpg);;BMP (*.bmp)"
        )
        if not path:
            return

        # Rendern
        image = self._engine.render_full(cell_size)

        if image.save(path):
            QMessageBox.information(
                self,
                "Export erfolgreich",
                f"Bild gespeichert:\n{path}\n\nGröße: {image.width()} × {image.height()} Pixel",
            )
        else:
            QMessageBox.critical(self, "Fehler", "Bild konnte nicht gespeichert werden.")
