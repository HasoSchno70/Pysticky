"""
User-Template Manager.

Ermöglicht das Speichern und Laden von eigenen Projekt-Templates.
Templates werden als JSON im Benutzerverzeichnis gespeichert.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ...core.i18n import t
from ...utils.logging import get_logger
from ..styles import THEME, Styles

logger = get_logger(__name__)


@dataclass
class UserTemplate:
    """Ein benutzerdefiniertes Template."""

    name: str
    width: int
    height: int
    fabric_count: int = 14
    description: str = ""
    category: str = "Eigene"


def get_templates_path() -> Path:
    """Gibt den Pfad zum Templates-Verzeichnis zurück.

    Nutzt den in Einstellungen → Dateien → "Templates" konfigurierten
    Ordner, falls gesetzt -- sonst den bisherigen Default im
    Benutzerverzeichnis.
    """
    from PySide6.QtCore import QSettings

    from ...config import APP_NAME, ORG_NAME

    configured = QSettings(ORG_NAME, APP_NAME).value("templates_path", "", type=str).strip()
    default_dir = Path.home() / ".pysticky" / "templates"
    templates_dir = Path(configured) if configured else default_dir
    try:
        templates_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        # Konfigurierter Ordner nicht (mehr) erreichbar (z.B. abgestecktes
        # Netzlaufwerk/USB-Stick, fehlende Berechtigung) -- "Neues Projekt"
        # und "Templates verwalten" duerfen dadurch nicht komplett
        # abstuerzen, sonst kommt der Nutzer gar nicht mehr an die
        # Einstellungen heran, um den Pfad zu korrigieren.
        logger.warning(
            "Templates-Ordner '%s' nicht erreichbar (%s), falle auf Standard zurueck",
            templates_dir,
            exc,
        )
        templates_dir = default_dir
        templates_dir.mkdir(parents=True, exist_ok=True)
    return templates_dir


def load_user_templates() -> list[UserTemplate]:
    """Lädt alle benutzerdefinierten Templates."""
    templates_path = get_templates_path() / "user_templates.json"

    if not templates_path.exists():
        return []

    try:
        with open(templates_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return []

    templates = []
    for entry in data:
        # Ein einzelner fehlerhafter Eintrag (fehlendes Pflichtfeld, alte
        # Formatversion) darf nicht das Laden ALLER Templates crashen lassen
        # -- gleiche Fehlerklasse wie LibraryData.from_dict().
        try:
            templates.append(UserTemplate(**entry))
        except TypeError as exc:
            logger.warning("Ungueltiges Template uebersprungen: %s", exc)
    return templates


def save_user_templates(templates: list[UserTemplate]) -> bool:
    """Speichert alle benutzerdefinierten Templates."""
    templates_path = get_templates_path() / "user_templates.json"

    try:
        with open(templates_path, "w", encoding="utf-8") as f:
            json.dump([asdict(t) for t in templates], f, indent=2, ensure_ascii=False)
        return True
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        # Aufrufer MUESSEN den Rueckgabewert pruefen (siehe misc_handlers.py
        # ::_on_save_as_template fuer das etablierte Muster) -- ohne dieses
        # Logging war ein Schreibfehler hier komplett unsichtbar, selbst im
        # Log, wenn ein Aufrufer den Rueckgabewert (noch) nicht prueft.
        logger.warning("Templates konnten nicht gespeichert werden: %s", exc)
        return False


class TemplatePreviewWidget(QFrame):
    """Kleine Vorschau eines Templates."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._width = 50
        self._height = 50
        self.setFixedSize(100, 80)
        self.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_medium};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
            }}
        """)

    def set_size(self, width: int, height: int) -> None:
        self._width = width
        self._height = height
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Skalierung berechnen
        max_w, max_h = 80, 60
        scale = min(max_w / self._width, max_h / self._height)

        draw_w = int(self._width * scale)
        draw_h = int(self._height * scale)

        x = (self.width() - draw_w) // 2
        y = (self.height() - draw_h) // 2

        # Rahmen
        painter.setPen(QColor(THEME.accent_primary))
        painter.setBrush(QColor(THEME.bg_light))
        painter.drawRect(x, y, draw_w, draw_h)

        # Raster andeuten
        painter.setPen(QColor(THEME.border_dark))
        step = max(4, draw_w // 8)
        for gx in range(x, x + draw_w, step):
            painter.drawLine(gx, y, gx, y + draw_h)
        for gy in range(y, y + draw_h, step):
            painter.drawLine(x, gy, x + draw_w, gy)


class SaveTemplateDialog(QDialog):
    """Dialog zum Speichern eines neuen Templates."""

    def __init__(
        self, width: int = 50, height: int = 50, fabric_count: int = 14, parent=None
    ) -> None:
        super().__init__(parent)
        self._template: UserTemplate | None = None

        self.setWindowTitle(t("Template speichern"))
        self.setMinimumWidth(400)

        self._setup_ui(width, height, fabric_count)
        self._apply_theme()

    def _setup_ui(self, width: int, height: int, fabric_count: int) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Vorschau
        preview_layout = QHBoxLayout()

        self._preview = TemplatePreviewWidget()
        self._preview.set_size(width, height)
        preview_layout.addWidget(self._preview)

        size_info = QLabel(f"{width} × {height} Stiche\nStoffzahl: {fabric_count}")
        size_info.setStyleSheet(f"color: {THEME.text_muted};")
        preview_layout.addWidget(size_info, 1)

        layout.addLayout(preview_layout)

        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel(t("Name:")))

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText(t("Mein Template"))
        name_layout.addWidget(self._name_input, 1)

        layout.addLayout(name_layout)

        # Kategorie
        cat_layout = QHBoxLayout()
        cat_layout.addWidget(QLabel(t("Kategorie:")))

        self._category_combo = QComboBox()
        self._category_combo.setEditable(True)
        self._category_combo.addItems(
            [
                t("Eigene"),
                t("Lesezeichen"),
                t("Deckchen"),
                t("Bordüren"),
                t("Bilder"),
                t("Kissen"),
                t("Accessoires"),
                t("Saisonal"),
            ]
        )
        cat_layout.addWidget(self._category_combo, 1)

        layout.addLayout(cat_layout)

        # Beschreibung
        layout.addWidget(QLabel(t("Beschreibung (optional):")))

        self._description_input = QTextEdit()
        self._description_input.setMaximumHeight(60)
        self._description_input.setPlaceholderText(t("Kurze Beschreibung des Templates..."))
        layout.addWidget(self._description_input)

        # Gespeicherte Werte
        self._width = width
        self._height = height
        self._fabric_count = fabric_count

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.reject)

        save_btn = QPushButton(t("Speichern"))
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)
        # _apply_theme() setzt einen eigenen dialogweiten QPushButton-Stil,
        # der die globale :default-Hervorhebung überschreibt.
        save_btn.setStyleSheet(Styles.button_primary())
        button_box.addButton(save_btn, QDialogButtonBox.ButtonRole.AcceptRole)

        btn_layout.addWidget(button_box)

        layout.addLayout(btn_layout)

    def _apply_theme(self) -> None:
        self.setStyleSheet(f"""
            QDialog {{
                background: {THEME.bg_dark};
            }}
            QLabel {{
                color: {THEME.text_primary};
            }}
            QLineEdit, QTextEdit, QComboBox {{
                background: {THEME.bg_medium};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
                padding: 8px;
            }}
            QPushButton {{
                background: {THEME.bg_medium};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background: {THEME.bg_light};
            }}
        """)

    def _on_save(self) -> None:
        name = self._name_input.text().strip()
        if not name:
            QMessageBox.warning(self, t("Fehler"), t("Bitte gib einen Namen ein."))
            return

        self._template = UserTemplate(
            name=name,
            width=self._width,
            height=self._height,
            fabric_count=self._fabric_count,
            description=self._description_input.toPlainText().strip(),
            category=self._category_combo.currentText(),
        )

        self.accept()

    @property
    def template(self) -> UserTemplate | None:
        return self._template


class ManageTemplatesDialog(QDialog):
    """Dialog zum Verwalten von benutzerdefinierten Templates."""

    templates_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._templates = load_user_templates()

        self.setWindowTitle(t("Templates verwalten"))
        self.setMinimumSize(500, 400)

        self._setup_ui()
        self._apply_theme()
        self._refresh_list()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Liste
        list_layout = QVBoxLayout()

        list_layout.addWidget(QLabel(t("Eigene Templates:")))

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_selection_changed)
        list_layout.addWidget(self._list, 1)

        layout.addLayout(list_layout, 1)

        # Details und Aktionen
        details_layout = QVBoxLayout()

        # Vorschau
        self._preview = TemplatePreviewWidget()
        details_layout.addWidget(self._preview)

        # Info
        self._info_label = QLabel(t("Kein Template ausgewählt"))
        self._info_label.setWordWrap(True)
        self._info_label.setStyleSheet(f"color: {THEME.text_muted};")
        details_layout.addWidget(self._info_label)

        details_layout.addStretch()

        # Buttons
        self._delete_btn = QPushButton(t("Löschen"))
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete)
        details_layout.addWidget(self._delete_btn)

        self._rename_btn = QPushButton(t("Umbenennen"))
        self._rename_btn.setEnabled(False)
        self._rename_btn.clicked.connect(self._on_rename)
        details_layout.addWidget(self._rename_btn)

        details_layout.addSpacing(20)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        details_layout.addWidget(button_box)

        layout.addLayout(details_layout)

    def _apply_theme(self) -> None:
        self.setStyleSheet(f"""
            QDialog {{
                background: {THEME.bg_dark};
            }}
            QLabel {{
                color: {THEME.text_primary};
            }}
            QListWidget {{
                background: {THEME.bg_medium};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
            }}
            QListWidget::item {{
                padding: 8px;
            }}
            QListWidget::item:selected {{
                background: {THEME.accent_primary};
            }}
            QPushButton {{
                background: {THEME.bg_medium};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background: {THEME.bg_light};
            }}
            QPushButton:disabled {{
                color: {THEME.text_muted};
            }}
        """)

    def _refresh_list(self) -> None:
        self._list.clear()
        for template in self._templates:
            item = QListWidgetItem(f"{template.name} ({template.width}×{template.height})")
            item.setData(Qt.ItemDataRole.UserRole, template)
            self._list.addItem(item)

    def _on_selection_changed(self, row: int) -> None:
        enabled = row >= 0
        self._delete_btn.setEnabled(enabled)
        self._rename_btn.setEnabled(enabled)

        if enabled and row < len(self._templates):
            template = self._templates[row]
            self._preview.set_size(template.width, template.height)
            info = f"<b>{template.name}</b><br>"
            info += f"{template.width} × {template.height} Stiche<br>"
            info += f"Stoffzahl: {template.fabric_count}<br>"
            if template.description:
                info += f"<br>{template.description}"
            self._info_label.setText(info)
        else:
            self._info_label.setText(t("Kein Template ausgewählt"))

    def _on_delete(self) -> None:
        row = self._list.currentRow()
        if row < 0:
            return

        template = self._templates[row]
        reply = QMessageBox.question(
            self,
            t("Löschen"),
            f"Template '{template.name}' wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self._templates[row]
            if not save_user_templates(self._templates):
                QMessageBox.warning(
                    self,
                    t("Fehler"),
                    t("Template konnte nicht gespeichert werden."),
                )
            self._refresh_list()
            self.templates_changed.emit()

    def _on_rename(self) -> None:
        row = self._list.currentRow()
        if row < 0:
            return

        template = self._templates[row]

        from PySide6.QtWidgets import QInputDialog

        new_name, ok = QInputDialog.getText(
            self, t("Umbenennen"), t("Neuer Name:"), text=template.name
        )

        if ok and new_name.strip():
            template.name = new_name.strip()
            if not save_user_templates(self._templates):
                QMessageBox.warning(
                    self,
                    t("Fehler"),
                    t("Template konnte nicht gespeichert werden."),
                )
            self._refresh_list()
            self.templates_changed.emit()
