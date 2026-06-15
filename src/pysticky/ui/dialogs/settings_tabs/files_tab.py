"""
Dateien-Tab für Settings-Dialog.
"""

from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ....core.constants import DEFAULT_MAX_IMPORT_COLORS, MAX_COLORS, MIN_COLORS
from ....core.i18n import t
from ._helpers import make_section_form


class FilesTab(QWidget):
    """Tab: Datei-Einstellungen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(4, 4, 4, 4)

        # === Pfade ===
        group_paths, form = make_section_form("Standardpfade", "📂")

        # Speicherort
        save_layout = QHBoxLayout()
        self.edit_default_path = QLineEdit()
        self.edit_default_path.setPlaceholderText(t("Standard-Speicherort"))
        self.edit_default_path.setToolTip(t("Standard-Ordner für Speichern/Öffnen"))
        btn_browse_save = QPushButton("...")
        btn_browse_save.setFixedWidth(30)
        btn_browse_save.clicked.connect(lambda: self._browse_folder(self.edit_default_path))
        save_layout.addWidget(self.edit_default_path)
        save_layout.addWidget(btn_browse_save)
        form.addRow(t("Speicherort:"), save_layout)

        # Muster-Bibliothek
        lib_layout = QHBoxLayout()
        self.edit_library_path = QLineEdit()
        self.edit_library_path.setPlaceholderText(t("Muster-Bibliothek Ordner"))
        self.edit_library_path.setToolTip(t("Ordner für die Muster-Bibliothek"))
        btn_browse_lib = QPushButton("...")
        btn_browse_lib.setFixedWidth(30)
        btn_browse_lib.clicked.connect(lambda: self._browse_folder(self.edit_library_path))
        lib_layout.addWidget(self.edit_library_path)
        lib_layout.addWidget(btn_browse_lib)
        form.addRow(t("Bibliothek:"), lib_layout)

        # Templates
        tmpl_layout = QHBoxLayout()
        self.edit_templates_path = QLineEdit()
        self.edit_templates_path.setPlaceholderText(t("Templates Ordner"))
        self.edit_templates_path.setToolTip(t("Ordner für Vorlagen"))
        btn_browse_tmpl = QPushButton("...")
        btn_browse_tmpl.setFixedWidth(30)
        btn_browse_tmpl.clicked.connect(lambda: self._browse_folder(self.edit_templates_path))
        tmpl_layout.addWidget(self.edit_templates_path)
        tmpl_layout.addWidget(btn_browse_tmpl)
        form.addRow(t("Templates:"), tmpl_layout)

        layout.addWidget(group_paths)

        # === Export ===
        group_export, form = make_section_form("Export", "📤")

        self.combo_pdf_quality = QComboBox()
        self.combo_pdf_quality.addItems(
            [t("Niedrig (72 dpi)"), t("Mittel (150 dpi)"), t("Hoch (300 dpi)")]
        )
        self.combo_pdf_quality.setCurrentIndex(2)
        self.combo_pdf_quality.setToolTip(t("Qualität für PDF-Export"))
        form.addRow(t("PDF-Qualität:"), self.combo_pdf_quality)

        self.spin_pdf_cells_per_page = QSpinBox()
        self.spin_pdf_cells_per_page.setRange(20, 60)
        self.spin_pdf_cells_per_page.setValue(40)
        self.spin_pdf_cells_per_page.setToolTip(t("Zellen pro Seite im PDF"))
        form.addRow(t("Zellen/Seite:"), self.spin_pdf_cells_per_page)

        self.chk_html_inline_css = QCheckBox(t("CSS inline einbetten"))
        self.chk_html_inline_css.setToolTip(t("Bettet CSS direkt in die HTML-Datei ein"))
        form.addRow(self.chk_html_inline_css)

        # Working-Chart-Page-Overlap fuer HTML/PDF (0 = aus)
        self.spin_page_overlap = QSpinBox()
        self.spin_page_overlap.setRange(0, 20)
        self.spin_page_overlap.setValue(0)
        self.spin_page_overlap.setSpecialValueText(t("aus"))
        self.spin_page_overlap.setToolTip(
            t(
                "Working-Chart-Konvention: jede Seite zeigt zusaetzlich die "
                "ersten N Stiche der Nachbarseite (rechts/unten). Erleichtert "
                "das Aneinanderlegen ausgedruckter Seiten.\n\n"
                "0 = aus, 5-10 = Standard fuer kommerzielle Patterns."
            )
        )
        form.addRow(t("Seiten-Overlap:"), self.spin_page_overlap)

        # Hersteller-Cross-Reference fuer HTML/PDF-Legende
        self.list_cross_ref = QListWidget()
        self.list_cross_ref.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.list_cross_ref.setToolTip(
            t(
                "Zusaetzliche Spalten in der Legende mit den jeweils naehesten\n"
                "Garn-Entsprechungen in anderen Hersteller-Paletten.\n"
                "Match per CIE-Lab-Delta-E — kein offizielles 1:1-Mapping."
            )
        )
        self.list_cross_ref.setMaximumHeight(120)
        self._populate_cross_ref_list()
        form.addRow(t("Cross-Reference:"), self.list_cross_ref)

        layout.addWidget(group_export)

        # === Import ===
        group_import, form = make_section_form("Import", "📥")

        self.spin_import_max_colors = QSpinBox()
        self.spin_import_max_colors.setRange(MIN_COLORS, MAX_COLORS)
        self.spin_import_max_colors.setValue(DEFAULT_MAX_IMPORT_COLORS)
        self.spin_import_max_colors.setToolTip(t("Maximale Farbanzahl beim Bildimport"))
        form.addRow(t("Max. Farben:"), self.spin_import_max_colors)

        self.combo_dither_method = QComboBox()
        self.combo_dither_method.addItems(
            [t("Kein Dithering"), t("Floyd-Steinberg"), t("Ordered Dithering")]
        )
        self.combo_dither_method.setToolTip(t("Dithering-Methode beim Bildimport"))
        form.addRow(t("Dithering:"), self.combo_dither_method)

        layout.addWidget(group_import)
        layout.addStretch()

    def _populate_cross_ref_list(self):
        """Fuellt die Cross-Reference-Liste mit den verfuegbaren Paletten."""
        from ....core.palette import get_palette_manager

        pm = get_palette_manager()
        pm.load_all()
        for name in sorted(pm.available_palettes):
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.list_cross_ref.addItem(item)

    def _get_cross_ref_selection(self) -> list[str]:
        """Liefert die Liste der aktivierten Cross-Reference-Paletten."""
        result = []
        for i in range(self.list_cross_ref.count()):
            item = self.list_cross_ref.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                result.append(item.text())
        return result

    def _set_cross_ref_selection(self, names: list[str]):
        """Setzt die Cross-Reference-Auswahl aus einer Namensliste."""
        names_set = set(names)
        for i in range(self.list_cross_ref.count()):
            item = self.list_cross_ref.item(i)
            item.setCheckState(
                Qt.CheckState.Checked if item.text() in names_set else Qt.CheckState.Unchecked
            )

    def _browse_folder(self, line_edit: QLineEdit):
        """Öffnet einen Ordner-Auswahl-Dialog."""
        folder = QFileDialog.getExistingDirectory(
            self, t("Ordner wählen"), line_edit.text() or str(Path.home())
        )
        if folder:
            line_edit.setText(folder)

    def load_settings(self, settings: QSettings):
        """Lädt Einstellungen."""
        self.edit_default_path.setText(
            settings.value("default_path", str(Path.home() / "Documents"))
        )
        self.edit_library_path.setText(settings.value("library_path", ""))
        self.edit_templates_path.setText(settings.value("templates_path", ""))
        self.combo_pdf_quality.setCurrentIndex(settings.value("pdf_quality", 2, type=int))
        self.spin_pdf_cells_per_page.setValue(settings.value("pdf_cells_per_page", 40, type=int))
        self.chk_html_inline_css.setChecked(settings.value("html_inline_css", True, type=bool))
        self.spin_import_max_colors.setValue(
            settings.value("import_max_colors", DEFAULT_MAX_IMPORT_COLORS, type=int)
        )
        self.combo_dither_method.setCurrentIndex(settings.value("dither_method", 1, type=int))
        # Cross-Reference: gespeichert als CSV-String
        cross_ref_csv = settings.value("export/cross_ref_palettes", "", type=str)
        self._set_cross_ref_selection([p.strip() for p in cross_ref_csv.split(",") if p.strip()])
        self.spin_page_overlap.setValue(settings.value("export/page_overlap_stitches", 0, type=int))

    def save_settings(self, settings: QSettings):
        """Speichert Einstellungen."""
        settings.setValue("default_path", self.edit_default_path.text())
        settings.setValue("library_path", self.edit_library_path.text())
        settings.setValue("templates_path", self.edit_templates_path.text())
        settings.setValue("pdf_quality", self.combo_pdf_quality.currentIndex())
        settings.setValue("pdf_cells_per_page", self.spin_pdf_cells_per_page.value())
        settings.setValue("html_inline_css", self.chk_html_inline_css.isChecked())
        settings.setValue("import_max_colors", self.spin_import_max_colors.value())
        settings.setValue("dither_method", self.combo_dither_method.currentIndex())
        settings.setValue(
            "export/cross_ref_palettes",
            ",".join(self._get_cross_ref_selection()),
        )
        settings.setValue("export/page_overlap_stitches", self.spin_page_overlap.value())

    def reset_to_defaults(self):
        """Setzt auf Standardwerte zurück."""
        self.edit_default_path.setText(str(Path.home() / "Documents"))
        self.edit_library_path.setText("")
        self.edit_templates_path.setText("")
        self.combo_pdf_quality.setCurrentIndex(2)
        self.spin_pdf_cells_per_page.setValue(40)
        self.chk_html_inline_css.setChecked(True)
        self.spin_import_max_colors.setValue(DEFAULT_MAX_IMPORT_COLORS)
        self.combo_dither_method.setCurrentIndex(1)
        self._set_cross_ref_selection([])
        self.spin_page_overlap.setValue(0)
