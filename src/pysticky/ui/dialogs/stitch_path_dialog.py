"""
Dialog für Stickpfad-Optimierung.

Ermöglicht die Auswahl der Optimierungsstrategie und zeigt
das Ergebnis mit Statistiken und Visualisierung an.
"""

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...config import UI_CONFIG
from ...core import (
    OptimizationResult,
    OptimizationStrategy,
    Pattern,
)
from ...core.constants import DEFAULT_FABRIC_COUNT, MAX_FABRIC_COUNT, MIN_FABRIC_COUNT
from ...core.i18n import t
from ...core.stitch_path_optimizer import StitchPathOptimizer
from ..styles import THEME
from ..widgets.path_preview import PathPreviewWidget
from ..workers import OptimizationWorker


class StitchPathDialog(QDialog):
    """Dialog für Stickpfad-Optimierung mit Threading."""

    show_path_on_canvas = Signal(object)

    def __init__(self, pattern: Pattern, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pattern = pattern
        self._result: OptimizationResult | None = None
        self._comparison_results: dict[str, OptimizationResult] | None = None

        # Threading
        self._worker: OptimizationWorker | None = None
        self._thread: QThread | None = None
        self._is_running = False

        self._setup_ui()
        self._apply_style()

        self.setWindowTitle(t("Stickpfad-Optimierung"))
        self.setMinimumSize(*UI_CONFIG.dialog_min_xlarge)
        self.resize(1200, 850)

    def _apply_style(self) -> None:
        self.setStyleSheet(f"""
            QDialog {{ background-color: {THEME.bg_medium}; color: {THEME.text_primary}; }}
            QGroupBox {{ background-color: {THEME.bg_light}; border: 1px solid {THEME.border_medium}; border-radius: 4px; margin-top: 12px; padding-top: 8px; color: {THEME.text_primary}; font-weight: bold; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}
            QLabel {{ color: {THEME.text_secondary}; }}
            QPushButton {{ background-color: {THEME.bg_lighter}; border: 1px solid {THEME.border_medium}; border-radius: 4px; padding: 6px 16px; color: {THEME.text_primary}; }}
            QPushButton:hover {{ background-color: {THEME.border_light}; border-color: {THEME.accent_primary}; }}
            QPushButton:disabled {{ background-color: {THEME.bg_dark}; color: {THEME.text_disabled}; }}
            QComboBox, QSpinBox {{ background-color: {THEME.bg_light}; border: 1px solid {THEME.border_medium}; border-radius: 4px; padding: 4px 8px; color: {THEME.text_primary}; }}
            QComboBox QAbstractItemView {{ background-color: {THEME.bg_light}; border: 1px solid {THEME.border_medium}; color: {THEME.text_primary}; selection-background-color: {THEME.accent_primary}; }}
            QTableWidget {{ background-color: {THEME.bg_dark}; border: 1px solid {THEME.border_medium}; border-radius: 4px; gridline-color: {THEME.border_dark}; color: {THEME.text_primary}; }}
            QTableWidget::item:selected {{ background-color: {THEME.accent_primary}; color: {THEME.bg_dark}; }}
            QHeaderView::section {{ background-color: {THEME.bg_light}; border: none; border-right: 1px solid {THEME.border_dark}; border-bottom: 1px solid {THEME.border_dark}; padding: 6px; color: {THEME.text_secondary}; font-weight: bold; }}
            QCheckBox {{ color: {THEME.text_secondary}; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {THEME.border_medium}; border-radius: 3px; background-color: {THEME.bg_light}; }}
            QCheckBox::indicator:checked {{ background-color: {THEME.accent_primary}; border-color: {THEME.accent_primary}; }}
            QProgressBar {{ border: 1px solid {THEME.border_medium}; border-radius: 4px; background-color: {THEME.bg_dark}; text-align: center; color: {THEME.text_primary}; }}
            QProgressBar::chunk {{ background-color: {THEME.accent_primary}; border-radius: 3px; }}
            QSplitter::handle {{ background-color: {THEME.border_medium}; }}
        """)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Einstellungen
        settings_group = QGroupBox(t("Einstellungen"))
        settings_layout = QHBoxLayout(settings_group)

        settings_layout.addWidget(QLabel(t("Strategie:")))
        self._strategy_combo = QComboBox()
        self._strategy_combo.addItem(
            t("Zeilenweise (Schlangenlinie)"), OptimizationStrategy.ROW_BY_ROW
        )
        self._strategy_combo.addItem(t("Nächster Nachbar"), OptimizationStrategy.NEAREST_NEIGHBOR)
        self._strategy_combo.addItem(t("Danish Method"), OptimizationStrategy.DANISH_METHOD)
        self._strategy_combo.addItem(t("Spaltenweise"), OptimizationStrategy.COLUMN_BY_COLUMN)
        self._strategy_combo.addItem(t("Diagonal"), OptimizationStrategy.DIAGONAL)
        self._strategy_combo.currentIndexChanged.connect(self._on_strategy_changed)
        settings_layout.addWidget(self._strategy_combo)

        settings_layout.addSpacing(20)
        settings_layout.addWidget(QLabel(t("Stoffzählung:")))
        self._fabric_spin = QSpinBox()
        self._fabric_spin.setRange(MIN_FABRIC_COUNT, MAX_FABRIC_COUNT)
        self._fabric_spin.setValue(DEFAULT_FABRIC_COUNT)
        self._fabric_spin.setSuffix(" ct")
        self._fabric_spin.valueChanged.connect(self._on_settings_changed)
        settings_layout.addWidget(self._fabric_spin)

        settings_layout.addStretch()

        self._optimize_btn = QPushButton(t("Optimieren"))
        self._optimize_btn.clicked.connect(self._run_optimization)
        settings_layout.addWidget(self._optimize_btn)

        self._compare_btn = QPushButton(t("Alle vergleichen"))
        self._compare_btn.clicked.connect(self._run_comparison)
        settings_layout.addWidget(self._compare_btn)

        self._cancel_btn = QPushButton(t("Abbrechen"))
        self._cancel_btn.clicked.connect(self._cancel_operation)
        self._cancel_btn.hide()
        settings_layout.addWidget(self._cancel_btn)

        layout.addWidget(settings_group)

        # Fortschrittsbalken
        self._progress_widget = QWidget()
        progress_layout = QHBoxLayout(self._progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setTextVisible(True)
        progress_layout.addWidget(self._progress_bar)

        self._progress_label = QLabel("")
        self._progress_label.setMinimumWidth(200)
        progress_layout.addWidget(self._progress_label)

        self._progress_widget.hide()
        layout.addWidget(self._progress_widget)

        # Vorschau-Header mit Optionen und Zoom
        preview_header = QHBoxLayout()
        preview_header.addWidget(QLabel(t("Pfad-Vorschau:")))
        preview_header.addStretch()

        self._show_numbers_cb = QCheckBox(t("Nummern"))
        self._show_numbers_cb.toggled.connect(self._on_preview_options_changed)
        preview_header.addWidget(self._show_numbers_cb)

        self._show_jumps_cb = QCheckBox(t("Sprünge"))
        self._show_jumps_cb.setChecked(True)
        self._show_jumps_cb.toggled.connect(self._on_preview_options_changed)
        preview_header.addWidget(self._show_jumps_cb)

        self._show_context_cb = QCheckBox(t("Kontext"))
        self._show_context_cb.setChecked(True)
        self._show_context_cb.toggled.connect(self._on_preview_options_changed)
        preview_header.addWidget(self._show_context_cb)

        preview_header.addSpacing(10)

        self._zoom_out_btn = QPushButton("−")
        self._zoom_out_btn.setFixedWidth(28)
        self._zoom_out_btn.clicked.connect(lambda: self._preview.zoom_out())
        preview_header.addWidget(self._zoom_out_btn)

        self._zoom_label = QLabel("100%")
        self._zoom_label.setFixedWidth(45)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_header.addWidget(self._zoom_label)

        self._zoom_in_btn = QPushButton("+")
        self._zoom_in_btn.setFixedWidth(28)
        self._zoom_in_btn.clicked.connect(lambda: self._preview.zoom_in())
        preview_header.addWidget(self._zoom_in_btn)

        self._zoom_fit_btn = QPushButton("⬜")
        self._zoom_fit_btn.setFixedWidth(28)
        self._zoom_fit_btn.clicked.connect(lambda: self._preview.fit_to_view())
        preview_header.addWidget(self._zoom_fit_btn)

        layout.addLayout(preview_header)

        # Vertikaler Splitter: Vorschau oben (groß), Tabelle unten (kompakt)
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Vorschau (nimmt den Hauptteil ein)
        self._preview = PathPreviewWidget()
        self._preview.set_pattern(self._pattern)
        self._preview.setMinimumHeight(300)
        self._preview.zoom_changed.connect(lambda z: self._zoom_label.setText(f"{z}%"))
        splitter.addWidget(self._preview)

        # Farbtabelle (kompakt unten)
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.setContentsMargins(0, 4, 0, 0)
        table_layout.addWidget(QLabel(t("Farben und Pfade:")))

        self._color_table = QTableWidget()
        self._color_table.setColumnCount(5)
        self._color_table.setHorizontalHeaderLabels(
            [t("Farbe"), t("Stiche"), t("Distanz"), t("Sprünge"), t("Garn (cm)")]
        )
        self._color_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._color_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._color_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._color_table.itemSelectionChanged.connect(self._on_color_selected)
        table_layout.addWidget(self._color_table)
        splitter.addWidget(table_widget)

        # Vorschau bekommt 70%, Tabelle 30%
        splitter.setSizes([500, 200])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        # Statistiken
        stats_group = QGroupBox(t("Zusammenfassung"))
        stats_layout = QHBoxLayout(stats_group)

        self._stats_labels = {}
        for key, label in [
            ("stitches", t("Stiche:")),
            ("colors", t("Farben:")),
            ("distance", t("Rückseiten-Distanz:")),
            ("jumps", t("Sprünge:")),
            ("thread", t("Geschätzter Garnverbrauch:")),
        ]:
            stats_layout.addWidget(QLabel(label))
            value_label = QLabel("-")
            value_label.setStyleSheet(f"font-weight: bold; color: {THEME.accent_primary};")
            self._stats_labels[key] = value_label
            stats_layout.addWidget(value_label)
            stats_layout.addSpacing(20)
        stats_layout.addStretch()
        layout.addWidget(stats_group)

        # Vergleich
        self._comparison_group = QGroupBox(t("Strategievergleich"))
        comparison_layout = QVBoxLayout(self._comparison_group)
        self._comparison_table = QTableWidget()
        self._comparison_table.setColumnCount(5)
        self._comparison_table.setHorizontalHeaderLabels(
            [t("Strategie"), t("Distanz"), t("Sprünge"), t("Garn (cm)"), t("Bewertung")]
        )
        self._comparison_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._comparison_table.setMaximumHeight(120)
        comparison_layout.addWidget(self._comparison_table)
        self._comparison_group.hide()
        layout.addWidget(self._comparison_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Export-Button mit Menü
        self._export_btn = QPushButton(t("Exportieren ▼"))
        self._export_btn.setEnabled(False)

        export_menu = QMenu(self)
        export_menu.addAction(t("Als Text exportieren (.txt)"), self._export_text)
        export_menu.addAction(t("Aktuellen Pfad als Bild (.png)"), self._export_current_image)
        export_menu.addAction(t("Alle Pfade als Bilder..."), self._export_all_images)
        self._export_btn.setMenu(export_menu)

        button_layout.addWidget(self._export_btn)

        close_btn = QPushButton(t("Schließen"))
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

    def _set_running(self, running: bool) -> None:
        """Setzt UI-Status während Berechnung."""
        self._is_running = running
        self._optimize_btn.setEnabled(not running)
        self._compare_btn.setEnabled(not running)
        self._strategy_combo.setEnabled(not running)
        self._fabric_spin.setEnabled(not running)
        self._cancel_btn.setVisible(running)
        self._progress_widget.setVisible(running)

        if running:
            self._progress_bar.setValue(0)
            self._progress_label.setText(t("Starte..."))

    def _start_worker(self) -> None:
        """Erstellt und startet Worker-Thread."""
        self._thread = QThread()
        self._worker = OptimizationWorker(self._pattern)
        self._worker.moveToThread(self._thread)

        # Verbinde Start-Signale (QueuedConnection damit sie im Worker-Thread laufen)
        self._worker.start_optimization.connect(
            self._worker._run_optimization, Qt.ConnectionType.QueuedConnection
        )
        self._worker.start_comparison.connect(
            self._worker._run_comparison, Qt.ConnectionType.QueuedConnection
        )

        # Verbinde Worker-Signale mit Dialog-Slots
        self._worker.progress.connect(self._on_progress, Qt.ConnectionType.QueuedConnection)
        self._worker.finished.connect(
            self._on_optimization_finished, Qt.ConnectionType.QueuedConnection
        )
        self._worker.comparison_finished.connect(
            self._on_comparison_finished, Qt.ConnectionType.QueuedConnection
        )

        # Thread-Cleanup
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _cleanup_worker(self) -> None:
        """Räumt Worker auf."""
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(1000)
        self._worker = None
        self._thread = None

    def _run_optimization(self) -> None:
        """Startet Optimierung im Hintergrund."""
        self._set_running(True)
        self._start_worker()

        strategy = self._strategy_combo.currentData()
        fabric_count = self._fabric_spin.value()

        # Im Thread ausführen über Signal
        self._worker.start_optimization.emit(strategy, fabric_count)

    def _run_comparison(self) -> None:
        """Startet Vergleich im Hintergrund."""
        self._set_running(True)
        self._start_worker()

        fabric_count = self._fabric_spin.value()
        # Im Thread ausführen über Signal
        self._worker.start_comparison.emit(fabric_count)

    def _cancel_operation(self) -> None:
        """Bricht laufende Operation ab."""
        if self._worker:
            self._worker.cancel()
        self._progress_label.setText(t("Abbrechen..."))

    def _on_progress(self, current: int, total: int, message: str) -> None:
        """Update Fortschrittsanzeige."""
        self._progress_bar.setValue(current)
        self._progress_label.setText(message)

    def _on_optimization_finished(self, result: OptimizationResult | None) -> None:
        """Optimierung abgeschlossen."""
        self._set_running(False)
        self._cleanup_worker()

        if result:
            self._result = result
            self._update_display()

    def _on_comparison_finished(self, results: dict[str, OptimizationResult] | None) -> None:
        """Vergleich abgeschlossen."""
        self._set_running(False)
        self._cleanup_worker()

        if results:
            self._comparison_results = results

            # Beste Strategie
            best_strategy = min(results.items(), key=lambda x: x[1].total_distance)

            for i in range(self._strategy_combo.count()):
                if self._strategy_combo.itemData(i).value == best_strategy[0]:
                    self._strategy_combo.blockSignals(True)
                    self._strategy_combo.setCurrentIndex(i)
                    self._strategy_combo.blockSignals(False)
                    break

            self._result = best_strategy[1]
            self._update_display()
            self._update_comparison_table()
            self._comparison_group.show()

    def _update_display(self) -> None:
        """Aktualisiert Anzeige."""
        if not self._result:
            return

        self._stats_labels["stitches"].setText(str(self._result.total_stitches))
        self._stats_labels["colors"].setText(str(len(self._result.color_paths)))
        self._stats_labels["distance"].setText(f"{self._result.total_distance:.1f}")
        self._stats_labels["jumps"].setText(str(self._result.total_jumps))
        self._stats_labels["thread"].setText(
            f"{self._result.estimated_thread_length:.0f} cm ({self._result.estimated_thread_length / 100:.1f} m)"
        )

        # Alle Pfade an Preview übergeben für Kontext-Darstellung
        self._preview.set_all_color_paths(self._result.color_paths)

        self._color_table.setRowCount(len(self._result.color_paths))

        # Garnfaktor berechnen (gleiche Formel wie im Optimizer)
        fabric_count = self._fabric_spin.value()
        count_factor = DEFAULT_FABRIC_COUNT / fabric_count

        # Maximum für Balkendiagramm ermitteln
        yarn_values = []
        for path in self._result.color_paths:
            yarn = (
                path.stitch_count * StitchPathOptimizer.THREAD_PER_STITCH_CM * count_factor
                + path.total_distance * 0.5 * count_factor
            )
            yarn_values.append(yarn)
        max_yarn = max(yarn_values) if yarn_values else 1

        for row, path in enumerate(self._result.color_paths):
            entry = self._pattern.get_color_entry(path.color_index)
            color_name = entry.thread.name if entry else f"Farbe {path.color_index}"

            color_item = QTableWidgetItem(color_name)
            if entry:
                tc = entry.thread.color
                color_item.setBackground(QColor(tc.r, tc.g, tc.b))
                color_item.setForeground(
                    QColor(0, 0, 0) if tc.luminance > 0.5 else QColor(255, 255, 255)
                )

            self._color_table.setItem(row, 0, color_item)
            self._color_table.setItem(row, 1, QTableWidgetItem(str(path.stitch_count)))
            self._color_table.setItem(row, 2, QTableWidgetItem(f"{path.total_distance:.1f}"))
            self._color_table.setItem(row, 3, QTableWidgetItem(str(path.jump_count)))

            # Garn-Spalte mit Balkendiagramm-Hintergrund
            yarn = yarn_values[row]
            yarn_item = QTableWidgetItem(f"{yarn:.0f}")
            ratio = yarn / max_yarn if max_yarn > 0 else 0
            # Farbverlauf: wenig Garn = grün, viel = orange/rot
            r = int(min(255, ratio * 400))
            g = int(max(0, 200 - ratio * 150))
            yarn_item.setBackground(QColor(r, g, 60, 80))
            self._color_table.setItem(row, 4, yarn_item)

        self._export_btn.setEnabled(True)
        if self._result.color_paths:
            self._color_table.selectRow(0)

    def _update_comparison_table(self) -> None:
        """Aktualisiert Vergleichstabelle."""
        if not self._comparison_results:
            return

        sorted_results = sorted(self._comparison_results.items(), key=lambda x: x[1].total_distance)
        self._comparison_table.setRowCount(len(sorted_results))
        best_distance = sorted_results[0][1].total_distance

        names = {
            "row_by_row": t("Zeilenweise"),
            "nearest": t("Nächster Nachbar"),
            "danish": t("Danish Method"),
            "column": t("Spaltenweise"),
            "diagonal": t("Diagonal"),
        }

        for row, (key, result) in enumerate(sorted_results):
            self._comparison_table.setItem(row, 0, QTableWidgetItem(names.get(key, key)))
            self._comparison_table.setItem(row, 1, QTableWidgetItem(f"{result.total_distance:.1f}"))
            self._comparison_table.setItem(row, 2, QTableWidgetItem(str(result.total_jumps)))
            self._comparison_table.setItem(
                row, 3, QTableWidgetItem(f"{result.estimated_thread_length:.0f}")
            )

            ratio = result.total_distance / best_distance if best_distance > 0 else 1
            rating = (
                "★★★ Beste"
                if ratio < 1.05
                else "★★ Gut"
                if ratio < 1.15
                else "★ OK"
                if ratio < 1.30
                else "—"
            )
            rating_item = QTableWidgetItem(rating)
            if "Beste" in rating:
                rating_item.setForeground(QColor(100, 255, 100))
            self._comparison_table.setItem(row, 4, rating_item)

    def _on_color_selected(self) -> None:
        if not self._result:
            return
        selected = self._color_table.selectionModel().selectedRows()
        if selected:
            row = selected[0].row()
            if row < len(self._result.color_paths):
                self._preview.set_color_path(self._result.color_paths[row])

    def _on_strategy_changed(self) -> None:
        if self._result and not self._is_running:
            self._run_optimization()

    def _on_settings_changed(self) -> None:
        if self._result and not self._is_running:
            self._run_optimization()

    def _on_preview_options_changed(self) -> None:
        self._preview.set_show_numbers(self._show_numbers_cb.isChecked())
        self._preview.set_show_jumps(self._show_jumps_cb.isChecked())
        self._preview.set_show_context(self._show_context_cb.isChecked())

    def _export_text(self) -> None:
        """Exportiert den Stickplan als Textdatei."""
        if not self._result:
            return

        from PySide6.QtWidgets import QFileDialog, QMessageBox

        filename, _ = QFileDialog.getSaveFileName(
            self, t("Stickplan als Text exportieren"), "", t("Textdatei (*.txt);;Alle Dateien (*)")
        )
        if not filename:
            return

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write("STICKPLAN - Optimierte Stichreihenfolge\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Strategie: {self._result.strategy.value}\n")
                f.write(f"Gesamtstiche: {self._result.total_stitches}\n")
                f.write(
                    f"Geschätzter Garnverbrauch: {self._result.estimated_thread_length:.0f} cm\n"
                )
                f.write(f"Anzahl Sprünge: {self._result.total_jumps}\n\n")

                for path in self._result.color_paths:
                    entry = self._pattern.get_color_entry(path.color_index)
                    color_name = entry.thread.name if entry else f"Farbe {path.color_index}"
                    f.write("-" * 60 + "\n")
                    f.write(f"FARBE: {color_name}\n")
                    f.write(f"Stiche: {path.stitch_count}, Sprünge: {path.jump_count}\n")
                    f.write("-" * 60 + "\n\n")
                    f.write("Nr.   Position    Distanz   Hinweis\n")
                    f.write("-" * 40 + "\n")
                    for step in path.steps:
                        f.write(
                            f"{step.step_number:4d}  ({step.x:3d},{step.y:3d})   "
                            f"{step.distance_from_prev:6.1f}   "
                            f"{' ← SPRUNG' if step.is_jump else ''}\n"
                        )
                    f.write("\n")
                f.write("=" * 60 + "\nEnde des Stickplans\n")

            QMessageBox.information(
                self, t("Export erfolgreich"), f"Stickplan wurde exportiert:\n{filename}"
            )
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, t("Fehler beim Export"), f"Fehler: {e}")

    def _export_current_image(self) -> None:
        """Exportiert den aktuell ausgewählten Pfad als PNG-Bild."""
        if not self._result or not self._preview._color_path:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, t("Kein Pfad"), t("Bitte wählen Sie zuerst eine Farbe aus."))
            return

        from PySide6.QtWidgets import QFileDialog, QMessageBox

        # Dateiname vorschlagen
        entry = self._pattern.get_color_entry(self._preview._color_path.color_index)
        default_name = (
            entry.thread.name if entry else f"farbe_{self._preview._color_path.color_index}"
        )
        default_name = default_name.replace(" ", "_").replace("/", "-")

        filename, _ = QFileDialog.getSaveFileName(
            self,
            t("Pfad als Bild exportieren"),
            f"stickpfad_{default_name}.png",
            t("PNG Bild (*.png);;Alle Dateien (*)"),
        )
        if not filename:
            return

        # Bild rendern und speichern
        image = self._preview.render_to_image(cell_size=15)
        if image:
            if image.save(filename):
                QMessageBox.information(
                    self, t("Export erfolgreich"), f"Pfad-Bild wurde exportiert:\n{filename}"
                )
            else:
                QMessageBox.critical(self, t("Fehler"), t("Bild konnte nicht gespeichert werden."))

    def _export_all_images(self) -> None:
        """Exportiert alle Pfade als PNG-Bilder in einen Ordner."""
        if not self._result:
            return

        import os

        from PySide6.QtWidgets import QFileDialog, QMessageBox

        # Ordner auswählen
        folder = QFileDialog.getExistingDirectory(self, t("Ordner für Pfad-Bilder auswählen"))
        if not folder:
            return

        # Alle Pfade exportieren
        exported = 0
        errors = []

        for i, path in enumerate(self._result.color_paths):
            # Pfad setzen für Rendering
            self._preview.set_color_path(path)

            # Dateiname erstellen
            entry = self._pattern.get_color_entry(path.color_index)
            color_name = entry.thread.name if entry else f"farbe_{path.color_index}"
            color_name = color_name.replace(" ", "_").replace("/", "-").replace("\\", "-")
            filename = os.path.join(folder, f"{i + 1:02d}_{color_name}.png")

            # Bild rendern und speichern
            image = self._preview.render_to_image(cell_size=15)
            if image and image.save(filename):
                exported += 1
            else:
                errors.append(color_name)

        # Erste Farbe wieder auswählen
        if self._result.color_paths:
            self._color_table.selectRow(0)

        # Ergebnis anzeigen
        if errors:
            QMessageBox.warning(
                self,
                t("Export teilweise erfolgreich"),
                f"{exported} von {len(self._result.color_paths)} Bildern exportiert.\n"
                f"Fehler bei: {', '.join(errors)}",
            )
        else:
            QMessageBox.information(
                self,
                t("Export erfolgreich"),
                f"Alle {exported} Pfad-Bilder wurden exportiert nach:\n{folder}",
            )

    def closeEvent(self, event) -> None:
        """Aufräumen beim Schließen."""
        if self._worker:
            self._worker.cancel()
        self._cleanup_worker()
        super().closeEvent(event)
