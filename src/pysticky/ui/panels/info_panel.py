"""
Info-Panel zur Anzeige von Muster-Informationen - Dunkles Design mit Gradient-Kacheln.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...core import Pattern
from ...core.constants import COMMON_FABRIC_COUNTS
from ...core.i18n import t
from ..styles import THEME, Styles
from .info_panel_widgets import SectionHeader, StatCard, _ColorListItem

__all__ = ["InfoPanel", "StatCard", "SectionHeader", "_ColorListItem"]


class InfoPanel(QWidget):
    """Panel zur Anzeige von Muster-Statistiken - Dunkles Design."""

    fabric_count_changed = Signal(int)
    color_clicked = Signal(int)  # Farb-Index in der Pattern-Palette
    FABRIC_COUNTS = COMMON_FABRIC_COUNTS

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pattern: Pattern | None = None
        self._color_items: list[_ColorListItem] = []
        self._selected_color_index: int | None = None
        # Modus: "stitch" (Kreuzstich) oder "diamond" (Diamond Painting).
        # Beeinflusst Labels (Stiche/Drills, Stickzeit/Klebezeit, ...) und
        # Berechnungen (Zeit pro Einheit, Garnbedarf vs. Drill-Anzahl).
        self._mode: str = "stitch"
        self._setup_ui()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(THEME.bg_medium))
        gradient.setColorAt(0.5, QColor(THEME.bg_dark))
        gradient.setColorAt(1, QColor(THEME.bg_dark))
        painter.fillRect(self.rect(), gradient)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # === Stoff-Auswahl (im DP-Modus: Drill-Größe) ===
        self._section_fabric = SectionHeader("🧵", t("STOFFZÄHLUNG"), THEME.accent_primary)
        layout.addWidget(self._section_fabric)

        self.combo_fabric = QComboBox()
        self.combo_fabric.setStyleSheet(Styles.combo_box())
        for count in self.FABRIC_COUNTS:
            self.combo_fabric.addItem(f"{count} ct Aida", count)
        self.combo_fabric.setCurrentIndex(1)
        self.combo_fabric.currentIndexChanged.connect(self._on_fabric_changed)
        layout.addWidget(self.combo_fabric)

        layout.addSpacing(6)

        # === Statistik-Karten ===
        self.card_stitches = StatCard("✦", t("Stiche"), THEME.accent_primary)
        layout.addWidget(self.card_stitches)

        self.card_colors = StatCard("🎨", t("Farben"), THEME.accent_secondary)
        layout.addWidget(self.card_colors)

        self.card_size = StatCard("📐", t("Größe"), THEME.info)
        layout.addWidget(self.card_size)

        self.card_cm = StatCard("📏", t("Maße"), THEME.accent_purple)
        layout.addWidget(self.card_cm)

        self.card_layers = StatCard("📑", t("Ebenen"), THEME.error)
        layout.addWidget(self.card_layers)

        self.card_time = StatCard("⏱", t("Stickzeit"), "#40c8b0")
        layout.addWidget(self.card_time)

        self.card_thread = StatCard("🧵", t("Garnbedarf"), "#c878a8")
        layout.addWidget(self.card_thread)

        self.card_progress = StatCard("✅", t("Fortschritt"), "#40c870")
        layout.addWidget(self.card_progress)

        self.card_difficulty = StatCard("🎯", t("Schwierigkeit"), THEME.warning)
        self.card_difficulty.setToolTip(
            t("Heuristik aus Farbanzahl, Spezial-Stichen, Backstitches und Größe.")
        )
        layout.addWidget(self.card_difficulty)

        # === Quell-Info — eine kompakte Zeile, Detail im Tooltip ===
        # Vorher: 3 Zeilen + Padding (~80 px). Jetzt: 1 Zeile (~28 px).
        # Die volle Info erscheint als HTML-Tooltip beim Hover.
        self.source_frame = QFrame()
        self.source_frame.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_light};
                border: 1px solid {THEME.border_medium};
                border-left: 4px solid {THEME.accent_secondary};
                border-radius: 8px;
            }}
        """)
        source_layout = QHBoxLayout(self.source_frame)
        source_layout.setContentsMargins(10, 6, 10, 6)
        source_layout.setSpacing(8)

        source_icon = QLabel("🖼️")
        source_icon.setStyleSheet("font-size: 13px; background: transparent;")
        source_layout.addWidget(source_icon)

        self.lbl_source_file = QLabel("")
        self.lbl_source_file.setStyleSheet(
            f"font-size: 11px; color: {THEME.text_secondary}; background: transparent;"
        )
        # Eliding via Qt-FontMetrics: zu langer Name wird in der Mitte gekürzt
        self.lbl_source_file.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        source_layout.addWidget(self.lbl_source_file, 1)

        # Status-Indikator (Datei OK / fehlt) als kleines Badge rechts
        self.lbl_source_status = QLabel("")
        self.lbl_source_status.setStyleSheet("font-size: 10px; background: transparent;")
        source_layout.addWidget(self.lbl_source_status)

        # Legacy-Referenz für das Palette-Label (wird in update genutzt) —
        # versteckt, wir packen die Info in den Tooltip.
        self.lbl_source_palette = QLabel("")
        self.lbl_source_palette.setVisible(False)

        self.source_frame.setVisible(False)
        layout.addWidget(self.source_frame)

        # === Farbübersicht ===
        self._section_colors = SectionHeader("📋", t("FARBÜBERSICHT"), THEME.info)
        layout.addWidget(self._section_colors)

        self.colors_frame = QFrame()
        self.colors_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {THEME.bg_light}, stop:1 {THEME.bg_dark});
                border: 1px solid {THEME.border_medium};
                border-radius: 12px;
            }}
        """)
        colors_layout = QVBoxLayout(self.colors_frame)
        colors_layout.setContentsMargins(12, 12, 12, 12)
        colors_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(150)
        # Kein setMaximumHeight — Frame darf auf verfügbaren Platz wachsen
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            {Styles.scrollbar()}
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.colors_list_layout = QVBoxLayout(scroll_content)
        self.colors_list_layout.setContentsMargins(2, 2, 2, 2)
        self.colors_list_layout.setSpacing(1)
        # Stretch am Ende — Items werden vor diesem stretch eingefügt,
        # damit sie oben anliegen statt vertikal verteilt zu werden
        self.colors_list_layout.addStretch()

        self._scroll_content = scroll_content  # für _update_colors_list

        scroll.setWidget(scroll_content)
        colors_layout.addWidget(scroll)

        # stretch=1 sorgt dafür dass die Farbübersicht den restlichen Platz
        # bis zum Panel-Boden ausfüllt (statt von einem addStretch hochgedrückt
        # zu werden).
        layout.addWidget(self.colors_frame, 1)

        self.setMinimumWidth(250)
        self.setMaximumWidth(340)

    def _apply_theme(self) -> None:
        """Re-applies all stylesheets for theme switching."""
        self._section_fabric._apply_theme(THEME.accent_primary)
        self._section_colors._apply_theme(THEME.info)
        self.combo_fabric.setStyleSheet(Styles.combo_box())
        self.source_frame.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_light};
                border: 1px solid {THEME.border_medium};
                border-left: 4px solid {THEME.accent_secondary};
                border-radius: 8px;
            }}
        """)
        # _update_source_info setzt die Datei-Label-Farbe je nach Status —
        # hier nur den Default für den noch-nicht-aktualisierten Fall.
        self.lbl_source_file.setStyleSheet(
            f"font-size: 11px; color: {THEME.text_secondary}; background: transparent;"
        )
        self.colors_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {THEME.bg_light}, stop:1 {THEME.bg_dark});
                border: 1px solid {THEME.border_medium};
                border-radius: 12px;
            }}
        """)
        # (lbl_colors_list existiert nicht mehr — Farbliste ist jetzt
        # eine Liste von _ColorListItem-Widgets, die sich selbst stylen)
        # Update StatCard labels
        for card in [
            self.card_stitches,
            self.card_colors,
            self.card_size,
            self.card_cm,
            self.card_layers,
            self.card_time,
            self.card_thread,
            self.card_progress,
            self.card_difficulty,
        ]:
            card._apply_theme()
        # Re-render color list with new theme colors
        if self._pattern:
            self._update_colors_list(self._pattern)
        self.update()

    def update_info(self, pattern: Pattern) -> None:
        self._pattern = pattern
        stats = pattern.get_statistics()

        # Zeige Stiche die gestickt werden (ohne übersprungene)
        stitches_to_do = stats["stitches_to_do"]
        if stats["skipped_stitches"] > 0:
            stitches_str = f"{stitches_to_do:,}".replace(",", ".")
            # Zeige übersprungene Stiche in Klammern
            self.card_stitches.set_value(f"{stitches_str} (+{stats['skipped_stitches']} überspr.)")
        else:
            stitches_str = f"{stats['total_stitches']:,}".replace(",", ".")
            self.card_stitches.set_value(stitches_str)

        # Farben: zeige auch übersprungene
        if stats["skipped_colors"] > 0:
            self.card_colors.set_value(
                f"{stats['used_colors']} / {stats['color_count']} ({stats['skipped_colors']} überspr.)"
            )
        else:
            self.card_colors.set_value(f"{stats['used_colors']} / {stats['color_count']}")

        self.card_size.set_value(f"{stats['width']} × {stats['height']}")
        self.card_cm.set_value(f"{stats['width_cm']:.1f} × {stats['height_cm']:.1f} cm")
        self.card_layers.set_value(f"{stats['layer_count']}")

        # Zeit nur für Stiche die gestickt werden
        time_str = self._calculate_stitch_time(stitches_to_do)
        self.card_time.set_value(time_str)

        thread_str = self._calculate_thread_usage(pattern)
        self.card_thread.set_value(thread_str)

        # Fortschritt
        progress_stats = pattern.get_progress_statistics()
        percent = progress_stats["progress_percent"]
        completed = progress_stats["completed_stitches"]
        total = progress_stats["total_stitches"]
        if total > 0:
            self.card_progress.set_value(f"{percent:.1f}% ({completed}/{total})")
        else:
            self.card_progress.set_value("0%")

        # Schwierigkeit (mit Score-Tooltip)
        from ...core.difficulty import compute_difficulty

        diff = compute_difficulty(pattern)
        self.card_difficulty.set_value(diff["level"])
        f = diff["factors"]
        d = diff["details"]
        self.card_difficulty.setToolTip(
            f"{t('Score')} {diff['score']}/12  —  "
            f"{t('Farben')} {f['colors']}/3, {t('Größe')} {f['size']}/3, "
            f"{t('Sonderstiche')} {f['special']}/3, {t('Backstitches')} {f['backstitches']}/3\n"
            f"({d['used_colors']} {t('Farben')}, {d['stitches_to_do']:,} {t('Stiche')}, "
            f"{d['special_ratio'] * 100:.1f}% {t('Sonder')}, {d['backstitches']} {t('Linien')})"
        )

        self._update_source_info(pattern)
        self._update_colors_list(pattern)

    def _calculate_stitch_time(self, stitches_to_do: int) -> str:
        """Berechnet die Arbeitszeit (Sticken oder Diamond Painting).

        Modus-abhängig:
        - Sticken: ~20s pro Kreuzstich (3 Stiche/min, mit Fadenwechsel)
        - Diamond: ~3s pro Drill (20 Drills/min, Hand-Tool-Tempo)
        """
        if stitches_to_do == 0:
            return "0 " + t("Min")

        seconds_per_unit = 3.0 if self._mode == "diamond" else 20.0
        total_seconds = stitches_to_do * seconds_per_unit
        total_minutes = total_seconds / 60
        hours = int(total_minutes // 60)
        minutes = int(total_minutes % 60)

        if hours >= 100:
            return f"~{hours} {t('Std')}"
        elif hours > 0:
            return f"~{hours}h {minutes}m"
        elif minutes > 0:
            return f"~{minutes} {t('Min')}"
        else:
            return "< 1 " + t("Min")

    def _calculate_thread_usage(self, pattern: Pattern) -> str:
        """Berechnet Garn-/Drill-Bedarf.

        Modus-abhängig:
        - Sticken: Garn-Bedarf in Metern (5 cm Garn pro Stich bei 14ct).
        - Diamond: Drill-Gesamtanzahl (alle DP-Drills + Reserve 10%).
        """
        total_stitches = sum(e.stitch_count for e in pattern.color_entries if not e.skip_stitching)

        if total_stitches == 0:
            return "0"

        if self._mode == "diamond":
            # 10% Reserve für verlorene/abgesprungene Drills
            total_drills = int(total_stitches * 1.10)
            return f"~{total_drills:,}".replace(",", ".") + " " + t("Drills")

        base_cm = 5.0 * (14 / pattern.fabric_count)
        total_cm = total_stitches * base_cm
        total_m = total_cm / 100
        total_m *= 1.15  # 15% Sicherheitszuschlag

        if total_m >= 100:
            return f"~{total_m:.0f} m"
        elif total_m >= 10:
            return f"~{total_m:.1f} m"
        else:
            return f"~{total_m:.2f} m"

    def _calculate_thread_per_color(
        self, stitch_count: int, fabric_count: int, mode: str = "stitch"
    ) -> str:
        if stitch_count == 0:
            return ""

        if mode == "diamond":
            # 10% Reserve, analog zum Gesamt-Drill-Bedarf in
            # _calculate_thread_usage() -- vorher fehlte hier jeder
            # Modus-Zweig, die Farbliste zeigte pro Diamond-Farbe eine
            # bedeutungslose Garn-Meterangabe (Aida-Formel) statt einer
            # Drill-Anzahl.
            total_drills = int(stitch_count * 1.10)
            return f"~{total_drills:,}".replace(",", ".")

        base_cm = 5.0 * (14 / fabric_count)
        total_cm = stitch_count * base_cm * 1.15
        total_m = total_cm / 100

        if total_m >= 10:
            return f"{total_m:.1f}m"
        elif total_m >= 1:
            return f"{total_m:.1f}m"
        else:
            return f"{total_cm:.0f}cm"

    def _update_source_info(self, pattern: Pattern) -> None:
        from pathlib import Path

        if not pattern.source_image_path:
            self.source_frame.setVisible(False)
            return

        self.source_frame.setVisible(True)
        source_path = Path(pattern.source_image_path)
        filename = source_path.name
        exists = source_path.exists()
        palette = pattern.source_palette_name or "—"

        # Eliding für den Dateinamen — bei langen Namen Mitte kürzen
        from PySide6.QtGui import QFontMetrics

        fm = QFontMetrics(self.lbl_source_file.font())
        elided = fm.elidedText(filename, Qt.TextElideMode.ElideMiddle, 200)
        self.lbl_source_file.setText(elided)
        self.lbl_source_file.setStyleSheet(
            f"font-size: 11px; "
            f"color: {THEME.text_secondary if exists else THEME.error}; "
            f"background: transparent;"
        )

        # Status-Badge: ✓ wenn Datei vorhanden, ⚠ wenn fehlt
        if exists:
            self.lbl_source_status.setText("✓")
            self.lbl_source_status.setStyleSheet(
                f"font-size: 11px; color: {THEME.accent_primary}; "
                f"font-weight: 700; background: transparent;"
            )
        else:
            self.lbl_source_status.setText("⚠")
            self.lbl_source_status.setStyleSheet(
                f"font-size: 12px; color: {THEME.warning}; "
                f"font-weight: 700; background: transparent;"
            )

        # Voller Tooltip mit Details
        status_line = (
            "✓ " + t("Datei vorhanden")
            if exists
            else f"<span style='color:#f87171'>⚠ {t('Datei nicht gefunden')}</span>"
        )
        self.source_frame.setToolTip(
            f"<b>{t('Importiert von:')}</b><br>"
            f"<code>{pattern.source_image_path}</code><br>"
            f"{status_line}<br>"
            f"<b>{t('Palette:')}</b> {palette}"
        )

    def _update_colors_list(self, pattern: Pattern) -> None:
        """Baut die kompakte Farbliste auf — incremental wenn möglich.

        WICHTIG: Bei jedem Stitch-Placed wird update_info() gerufen → diese
        Methode auch. Wenn wir hier alle Items neu erstellen, blinkt jedes
        Widget kurz top-level auf (Default-Title 'PySticky' im Window-Manager
        sichtbar als Phantom-Fenster). Deshalb: incremental updaten wenn die
        Farb-Anzahl + Identität gleich bleibt; nur bei echter Strukturänderung
        komplett neu bauen.
        """
        entries = pattern.color_entries

        # Schnell-Pfad: gleiche Anzahl Items wie Farben + alle sind ColorListItems
        # UND alle haben den aktuellen Modus (sonst müssen Symbol-Spalten
        # neu gerendert werden -> Rebuild nötig).
        same_structure = (
            len(self._color_items) == len(entries)
            and all(isinstance(it, _ColorListItem) for it in self._color_items)
            and all(getattr(it, "_mode", "stitch") == self._mode for it in self._color_items)
        )

        if same_structure and entries:
            # Nur Werte aktualisieren — keine Widget-Erzeugung, kein Phantom
            for i, (item, entry) in enumerate(zip(self._color_items, entries)):
                if isinstance(item, _ColorListItem):
                    item.update_entry(
                        entry,
                        pattern.fabric_count,
                        self._calculate_thread_per_color,
                    )
            return

        # Strukturänderung (Farbe hinzu/weg, Pattern-Wechsel): komplett neu.
        # Hier wird nur ausgeführt wenn sich die Farb-Anzahl wirklich ändert,
        # nicht bei normalen Stitch-Placeds.
        #
        # WICHTIG: setUpdatesEnabled(False) auf den Scroll-Content wrappen,
        # damit Qt während des Rebuilds keine frisch-konstruierten
        # ColorListItems als Top-Level-Fenster flickert. Das war die
        # Quelle des "leeres Fenster poppt kurz auf"-Phantoms.
        scroll_content = self._scroll_content
        scroll_content.setUpdatesEnabled(False)
        try:
            for item in self._color_items:
                # WICHTIG: kein setParent(None) — das macht das Widget top-level
                # und triggert das Phantom-Window. Stattdessen hide + remove + delete.
                self.colors_list_layout.removeWidget(item)
                item.hide()
                item.deleteLater()
            self._color_items.clear()

            if not entries:
                placeholder = QLabel(t("Keine Farben"))
                placeholder.setStyleSheet(
                    f"color: {THEME.text_disabled}; font-style: italic; padding: 8px; background: transparent;"
                )
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.colors_list_layout.insertWidget(0, placeholder)
                self._color_items.append(placeholder)
                return

            insert_pos = self.colors_list_layout.count() - 1  # vor stretch
            for i, entry in enumerate(entries):
                item = _ColorListItem(
                    index=i,
                    entry=entry,
                    fabric_count=pattern.fabric_count,
                    calc_thread_fn=self._calculate_thread_per_color,
                    parent=self._scroll_content,
                    mode=self._mode,
                )
                item.clicked.connect(self.color_clicked.emit)
                if i == self._selected_color_index:
                    item.set_selected(True)
                self.colors_list_layout.insertWidget(insert_pos, item)
                insert_pos += 1
                self._color_items.append(item)
        finally:
            scroll_content.setUpdatesEnabled(True)

    def set_selected_color(self, index: int) -> None:
        """Markiert die aktive Farbe in der Übersicht (synchron mit ColorBar)
        und scrollt sie sichtbar."""
        self._selected_color_index = index
        target_item = None
        for i, item in enumerate(self._color_items):
            if isinstance(item, _ColorListItem):
                is_target = i == index
                item.set_selected(is_target)
                if is_target:
                    target_item = item
        # Scroll-Area-Parent finden und Item sichtbar scrollen
        if target_item is not None:
            scroll = target_item.parentWidget()
            while scroll is not None and not isinstance(scroll, QScrollArea):
                scroll = scroll.parentWidget()
            if scroll is not None:
                scroll.ensureWidgetVisible(target_item, 0, 30)

    def set_mode(self, mode: str) -> None:
        """Schaltet das Panel zwischen Kreuzstich- und Diamond-Painting-Modus.

        Ändert Labels (Stiche/Drills, Stickzeit/Klebezeit, Stoff/Drill-Raster),
        Combobox-Inhalte (Aida-Counts vs. Drill-Größen) und die zugrunde-
        liegenden Zeit-/Verbrauchs-Berechnungen.

        Args:
            mode: "stitch" oder "diamond". Unbekannte Werte werden ignoriert.
        """
        if mode not in ("stitch", "diamond"):
            return
        if mode == self._mode:
            # Bereits im richtigen Modus — keine UI-Aktion nötig (vermeidet
            # Flackern beim wiederholten _apply_pattern_mode-Call).
            return
        self._mode = mode

        is_dp = mode == "diamond"

        # Section-Header
        if is_dp:
            self._section_fabric.set_icon("💎")
            self._section_fabric.set_title(t("DRILL-RASTER"))
        else:
            self._section_fabric.set_icon("🧵")
            self._section_fabric.set_title(t("STOFFZÄHLUNG"))

        # Stat-Cards: Icons + Labels umstellen
        if is_dp:
            self.card_stitches.set_icon("💎")
            self.card_stitches.set_label(t("Drills"))
            self.card_time.set_label(t("Klebezeit"))
            self.card_thread.set_icon("📦")
            self.card_thread.set_label(t("Drill-Bedarf"))
            # Fortschritt im DP-Modus weg — kein klassischer
            # "Stich-abhaken"-Workflow vorhanden.
            self.card_progress.setVisible(False)
        else:
            self.card_stitches.set_icon("✦")
            self.card_stitches.set_label(t("Stiche"))
            self.card_time.set_label(t("Stickzeit"))
            self.card_thread.set_icon("🧵")
            self.card_thread.set_label(t("Garnbedarf"))
            self.card_progress.setVisible(True)

        # Fabric-Combo neu befüllen — die Inhalte sind modus-spezifisch.
        # Im DP-Modus: Drill-Größen (Standard 2.5mm Square, plus Round-Drill-
        # und seltener Mini-Drill-Raster). Im Stitch-Modus: Aida-Counts.
        self.combo_fabric.blockSignals(True)
        self.combo_fabric.clear()
        if is_dp:
            # Drill-Pitch-Werte als Aida-equivalente Zählung ablegen, damit
            # die existierende Garn-Verbrauchs-Logik durchläuft ohne Spezial-
            # Behandlung. Äquivalenz: 2.5mm-Drill ≈ 10ct, 2.8mm ≈ 9ct.
            self.combo_fabric.addItem(t("2.5 mm Square (Standard)"), 10)
            self.combo_fabric.addItem(t("2.8 mm Round"), 9)
            self.combo_fabric.addItem(t("3.0 mm Round"), 8)
        else:
            for count in self.FABRIC_COUNTS:
                self.combo_fabric.addItem(f"{count} ct Aida", count)
        # Auf passenden Default-Index gehen (im DP-Mode: erstes Item).
        if self._pattern is not None:
            for i in range(self.combo_fabric.count()):
                if self.combo_fabric.itemData(i) == self._pattern.fabric_count:
                    self.combo_fabric.setCurrentIndex(i)
                    break
            else:
                self.combo_fabric.setCurrentIndex(0)
        else:
            self.combo_fabric.setCurrentIndex(0)
        self.combo_fabric.blockSignals(False)

    def _on_fabric_changed(self, index: int) -> None:
        count = self.combo_fabric.currentData()
        if self._pattern:
            self._pattern.fabric_count = count
            self.update_info(self._pattern)
        self.fabric_count_changed.emit(count)

    def clear_info(self) -> None:
        self.card_stitches.set_value("0")
        self.card_colors.set_value("0")
        self.card_size.set_value("0 × 0")
        self.card_cm.set_value("0 × 0 cm")
        self.card_layers.set_value("0")
        self.card_time.set_value("0 " + t("Min"))
        self.card_thread.set_value("0" if self._mode == "diamond" else "0 m")
        self.card_progress.set_value("0%")
        self.card_difficulty.set_value("-")
        self.card_difficulty.setToolTip("")
        self.source_frame.setVisible(False)
        # Farbitems entsorgen
        for item in self._color_items:
            item.setParent(None)
            item.deleteLater()
        self._color_items.clear()
        self._selected_color_index = None
