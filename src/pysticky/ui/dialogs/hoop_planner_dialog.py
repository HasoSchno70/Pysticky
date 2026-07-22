"""
Rahmenaufteilung-Dialog: zeigt wie ein grosses Muster in mehrere
Stickrahmen-Sektoren aufgeteilt werden kann.

User stellt Rahmen-Größe + Überlappung ein, sieht eine grafische
Vorschau mit nummerierten Sektoren und eine tabellarische Übersicht.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ...core.hoop_planner import HoopPlan, plan_hoops
from ...core.i18n import t
from ..color_utils import to_qcolor
from ..styles import THEME

if TYPE_CHECKING:
    from ...core import Pattern


class _HoopPreviewWidget(QFrame):
    """Vorschau-Widget: zeichnet das Pattern in Mini-Form mit Sektor-Overlay."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pattern: "Pattern | None" = None
        self._plan: HoopPlan | None = None
        self._pattern_image: QImage | None = None
        self.setMinimumSize(360, 280)
        self.setStyleSheet(
            f"background: {THEME.bg_medium}; border: 1px solid {THEME.border_medium}; border-radius: 6px;"
        )

    def set_pattern(self, pattern: "Pattern") -> None:
        self._pattern = pattern
        self._pattern_image = self._render_pattern_thumb(pattern)
        self.update()

    def set_plan(self, plan: HoopPlan) -> None:
        self._plan = plan
        self.update()

    def _render_pattern_thumb(self, pattern: "Pattern") -> QImage:
        """Erzeugt ein kleines Pixel-Bild des Musters für die Vorschau."""
        from ...core.layer import NO_STITCH

        w, h = pattern.width, pattern.height
        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(QColor(245, 245, 240))
        composite = pattern.layer_stack.get_composite_grid()
        for y in range(h):
            for x in range(w):
                index = int(composite[y, x])
                if index == NO_STITCH or index >= len(pattern.color_entries):
                    continue
                c = pattern.color_entries[index].thread.color
                img.setPixelColor(x, y, to_qcolor(c))
        return img

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self._pattern is None or self._pattern_image is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Verfügbarer Bereich mit Rand
        margin = 16
        avail_w = self.width() - 2 * margin
        avail_h = self.height() - 2 * margin
        pw = self._pattern.width
        ph = self._pattern.height
        if pw == 0 or ph == 0:
            return
        scale = min(avail_w / pw, avail_h / ph)
        draw_w = int(pw * scale)
        draw_h = int(ph * scale)
        offset_x = (self.width() - draw_w) // 2
        offset_y = (self.height() - draw_h) // 2

        # Pattern-Thumb zeichnen
        pixmap = QPixmap.fromImage(self._pattern_image).scaled(
            draw_w,
            draw_h,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        painter.drawPixmap(offset_x, offset_y, pixmap)

        # Rand um Pattern
        painter.setPen(QPen(QColor(THEME.border_dark), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(offset_x - 1, offset_y - 1, draw_w + 1, draw_h + 1)

        # Sektoren-Overlay
        if self._plan is None or self._plan.fits_single_hoop:
            # Keine Aufteilung nötig — Hinweis
            painter.setPen(QColor(THEME.success))
            font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(
                self.rect().adjusted(0, 6, 0, 0),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                t("✓ Passt in einen Rahmen"),
            )
            return

        # Jeden Sektor mit Akzent-Rahmen + Nummer
        accent = QColor(THEME.accent_primary)
        for sector in self._plan.sectors:
            sx = offset_x + int(sector.x_start * scale)
            sy = offset_y + int(sector.y_start * scale)
            sw = int(sector.width * scale)
            sh = int(sector.height * scale)
            # Halbtransparenter Füll
            fill = QColor(accent)
            fill.setAlpha(40 + (sector.index % 2) * 20)
            painter.setBrush(fill)
            painter.setPen(QPen(accent, 2))
            painter.drawRect(sx, sy, sw, sh)

            # Sektor-Nummer in der Mitte
            label = str(sector.index + 1)
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Segoe UI", 11, QFont.Weight.Bold)
            painter.setFont(font)
            text_rect = painter.fontMetrics().boundingRect(label)
            # Hintergrund-Kreis für Lesbarkeit
            cx = sx + sw // 2
            cy = sy + sh // 2
            r = max(text_rect.width(), text_rect.height()) // 2 + 6
            painter.setBrush(QColor(0, 0, 0, 160))
            painter.setPen(QPen(accent, 2))
            painter.drawEllipse(cx - r, cy - r, 2 * r, 2 * r)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(
                sx,
                sy,
                sw,
                sh,
                Qt.AlignmentFlag.AlignCenter,
                label,
            )


class HoopPlannerDialog(QDialog):
    """Dialog zum Aufteilen grosser Muster auf mehrere Stickrahmen."""

    # Gängige Hoop-Größen, kalibriert auf Aida 14 ct (~5.5 Stiche/cm).
    # Die tatsächlichen Stich-Werte pro Preset-Button werden in _setup_ui()
    # mit pattern.fabric_count / 14 skaliert -- ohne diese Skalierung waren
    # die cm-Beschriftungen der Presets für jede Stoffzählung außer 14 ct
    # schlicht falsch (z.B. "8 Zoll (20 cm)" ergab bei 18 ct einen Rahmen,
    # der real keine 8 Zoll misst).
    COMMON_HOOPS = [
        ("4 Zoll (10 cm)", 55, 55),
        ("5 Zoll (13 cm)", 71, 71),
        ("6 Zoll (15 cm)", 82, 82),
        ("7 Zoll (18 cm)", 99, 99),
        ("8 Zoll (20 cm)", 110, 110),
        ("10 Zoll (25 cm)", 137, 137),
        ("12 Zoll (30 cm)", 165, 165),
    ]

    def __init__(self, pattern: "Pattern", parent=None) -> None:
        super().__init__(parent)
        self._pattern = pattern
        self._hoop_scale = pattern.fabric_count / 14

        self.setWindowTitle(t("Rahmenaufteilung"))
        self.setMinimumSize(820, 600)
        self._setup_ui()
        self._recalculate()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        intro = QLabel(
            f"Pattern-Größe: <b>{self._pattern.width} × {self._pattern.height}</b> Stiche "
            f"({self._pattern.fabric_count} ct). "
            "Wähle deine Stickrahmen-Größe und die Überlappungs-Zone — die Aufteilung "
            "wird automatisch berechnet."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # Eingabe-Block + Vorschau nebeneinander
        body = QHBoxLayout()
        body.setSpacing(14)

        # === Linke Spalte: Eingaben ===
        left = QVBoxLayout()
        left.setSpacing(8)

        form = QFormLayout()
        form.setSpacing(8)

        # Preset-Buttons
        preset_row = QHBoxLayout()
        preset_row.setSpacing(4)
        preset_row.addWidget(QLabel(t("Schnellwahl:")))
        for label, w, h in self.COMMON_HOOPS[:4]:
            btn = QPushButton(t(label))
            btn.setProperty("hoop_w", round(w * self._hoop_scale))
            btn.setProperty("hoop_h", round(h * self._hoop_scale))
            btn.clicked.connect(self._apply_preset)
            preset_row.addWidget(btn)
        preset_row.addStretch(1)
        left.addLayout(preset_row)

        preset_row2 = QHBoxLayout()
        preset_row2.setSpacing(4)
        preset_row2.addWidget(QLabel(""))
        for label, w, h in self.COMMON_HOOPS[4:]:
            btn = QPushButton(t(label))
            btn.setProperty("hoop_w", round(w * self._hoop_scale))
            btn.setProperty("hoop_h", round(h * self._hoop_scale))
            btn.clicked.connect(self._apply_preset)
            preset_row2.addWidget(btn)
        preset_row2.addStretch(1)
        left.addLayout(preset_row2)

        # Default = "6 Zoll (15 cm)"-Preset, skaliert auf die tatsaechliche
        # Stoffzaehlung (siehe COMMON_HOOPS-Kommentar).
        default_hoop = round(82 * self._hoop_scale)

        self.spin_w = QSpinBox()
        self.spin_w.setRange(10, 500)
        self.spin_w.setValue(default_hoop)
        self.spin_w.setSuffix(t(" Stiche"))
        self.spin_w.valueChanged.connect(self._recalculate)
        form.addRow(t("Rahmen-Breite:"), self.spin_w)

        self.spin_h = QSpinBox()
        self.spin_h.setRange(10, 500)
        self.spin_h.setValue(default_hoop)
        self.spin_h.setSuffix(t(" Stiche"))
        self.spin_h.valueChanged.connect(self._recalculate)
        form.addRow(t("Rahmen-Höhe:"), self.spin_h)

        self.spin_overlap = QSpinBox()
        self.spin_overlap.setRange(0, 50)
        self.spin_overlap.setValue(3)
        self.spin_overlap.setSuffix(t(" Stiche"))
        self.spin_overlap.setToolTip(
            t(
                "Anzahl Stiche die zwei benachbarte Sektoren teilen — "
                "verhindert sichtbare Nähte. Empfehlung: 2-5."
            )
        )
        self.spin_overlap.valueChanged.connect(self._recalculate)
        form.addRow(t("Überlappung:"), self.spin_overlap)

        left.addLayout(form)

        self.summary_label = QLabel()
        self.summary_label.setStyleSheet(
            f"color: {THEME.accent_primary}; font-size: 13px; font-weight: 600; padding: 8px;"
        )
        self.summary_label.setWordWrap(True)
        left.addWidget(self.summary_label)

        # Sektoren-Tabelle
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["#", t("Position"), t("X-Bereich"), t("Y-Bereich"), t("Stiche")]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        left.addWidget(self.table, 1)

        body.addLayout(left, 1)

        # === Rechte Spalte: Vorschau ===
        right = QVBoxLayout()
        right.addWidget(QLabel(t("Vorschau:")))
        self.preview = _HoopPreviewWidget()
        right.addWidget(self.preview, 1)
        body.addLayout(right, 1)

        layout.addLayout(body, 1)

        # Dialog-Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        self.preview.set_pattern(self._pattern)

    def _apply_preset(self) -> None:
        btn = self.sender()
        if btn is None:
            return
        w = btn.property("hoop_w")
        h = btn.property("hoop_h")
        if w and h:
            self.spin_w.blockSignals(True)
            self.spin_h.blockSignals(True)
            self.spin_w.setValue(int(w))
            self.spin_h.setValue(int(h))
            self.spin_w.blockSignals(False)
            self.spin_h.blockSignals(False)
            self._recalculate()

    def _recalculate(self) -> None:
        hw = self.spin_w.value()
        hh = self.spin_h.value()
        ov = self.spin_overlap.value()
        # Overlap darf nicht >= Hoop-Größe — auto-clampen
        max_ov = min(hw, hh) - 1
        if ov > max_ov:
            self.spin_overlap.blockSignals(True)
            self.spin_overlap.setValue(max(0, max_ov))
            self.spin_overlap.blockSignals(False)
            ov = self.spin_overlap.value()

        try:
            plan = plan_hoops(self._pattern, hw, hh, ov)
        except ValueError as e:
            self.summary_label.setText(f"⚠ {e}")
            self.preview.set_plan(None)  # type: ignore[arg-type]
            self.table.setRowCount(0)
            return

        self._update_summary(plan)
        self._update_table(plan)
        self.preview.set_plan(plan)

    def _update_summary(self, plan: HoopPlan) -> None:
        if plan.fits_single_hoop:
            self.summary_label.setText(
                f"✓ Das gesamte Muster passt in <b>einen</b> Stickrahmen "
                f"({plan.hoop_width}×{plan.hoop_height})."
            )
        else:
            self.summary_label.setText(
                f"<b>{plan.total_sectors}</b> Stickrahmen-Sektoren benötigt "
                f"({plan.rows} Reihen × {plan.cols} Spalten, "
                f"Überlappung {plan.overlap} Stiche)."
            )

    def _update_table(self, plan: HoopPlan) -> None:
        self.table.setRowCount(len(plan.sectors))
        for row, s in enumerate(plan.sectors):
            self.table.setItem(row, 0, QTableWidgetItem(str(s.index + 1)))
            self.table.setItem(row, 1, QTableWidgetItem(f"R{s.row + 1} S{s.col + 1}"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{s.x_start} … {s.x_end - 1}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{s.y_start} … {s.y_end - 1}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{s.stitch_count}"))
