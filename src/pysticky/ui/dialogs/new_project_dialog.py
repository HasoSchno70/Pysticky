"""
Dialog für neues Projekt mit Template-Auswahl.

Bietet:
- Vordefinierte Templates (Lesezeichen, Deckchen, Bordüren, etc.)
- Benutzerdefinierte Größe
- Stoffart-Auswahl
- Vorschau
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...config import UI_CONFIG
from ...core.constants import COMMON_FABRIC_COUNTS, MAX_PATTERN_SIZE
from ...core.i18n import t
from ..styles import THEME, Styles
from .user_template_dialog import load_user_templates

# Vordefinierte Templates
TEMPLATES = {
    "Lesezeichen": [
        {
            "name": "Lesezeichen Klein",
            "width": 25,
            "height": 80,
            "icon": "📑",
            "desc": "Schmales Lesezeichen",
        },
        {
            "name": "Lesezeichen Standard",
            "width": 30,
            "height": 100,
            "icon": "📖",
            "desc": "Klassisches Format",
        },
        {
            "name": "Lesezeichen Breit",
            "width": 40,
            "height": 120,
            "icon": "📚",
            "desc": "Breites Lesezeichen mit Platz für Motive",
        },
    ],
    "Deckchen": [
        {
            "name": "Untersetzer Rund",
            "width": 40,
            "height": 40,
            "icon": "⭕",
            "desc": "Quadratisch für runde Untersetzer",
        },
        {
            "name": "Untersetzer Groß",
            "width": 60,
            "height": 60,
            "icon": "🔲",
            "desc": "Größerer Untersetzer",
        },
        {
            "name": "Deckchen Klein",
            "width": 80,
            "height": 80,
            "icon": "🏠",
            "desc": "Kleines Zierdeckchen",
        },
        {
            "name": "Deckchen Mittel",
            "width": 120,
            "height": 120,
            "icon": "🎀",
            "desc": "Mittleres Deckchen für Tische",
        },
        {
            "name": "Tischläufer Kurz",
            "width": 40,
            "height": 150,
            "icon": "➡️",
            "desc": "Kurzer Tischläufer",
        },
        {
            "name": "Tischläufer Lang",
            "width": 40,
            "height": 250,
            "icon": "↔️",
            "desc": "Langer Tischläufer",
        },
    ],
    "Bordüren": [
        {
            "name": "Bordüre Schmal",
            "width": 20,
            "height": 200,
            "icon": "📏",
            "desc": "Schmale Zierbordüre",
        },
        {
            "name": "Bordüre Mittel",
            "width": 35,
            "height": 200,
            "icon": "🎗️",
            "desc": "Mittlere Bordüre",
        },
        {
            "name": "Bordüre Breit",
            "width": 50,
            "height": 200,
            "icon": "🎞️",
            "desc": "Breite Bordüre für Handtücher",
        },
        {
            "name": "Borte Endlos",
            "width": 30,
            "height": 400,
            "icon": "♾️",
            "desc": "Lange Borte zum Wiederholen",
        },
    ],
    "Bilder": [
        {
            "name": "Mini-Bild",
            "width": 40,
            "height": 40,
            "icon": "🖼️",
            "desc": "Kleines Motiv, Ornament",
        },
        {
            "name": "Kleines Bild",
            "width": 60,
            "height": 80,
            "icon": "🎨",
            "desc": "Postkartengröße",
        },
        {"name": "Mittleres Bild", "width": 100, "height": 120, "icon": "🖼️", "desc": "A5-Format"},
        {"name": "Großes Bild", "width": 150, "height": 200, "icon": "🎭", "desc": "A4-Format"},
        {"name": "Wandbild", "width": 200, "height": 250, "icon": "🏛️", "desc": "Großes Wandbild"},
    ],
    "Kissen": [
        {
            "name": "Nadelkissen",
            "width": 30,
            "height": 30,
            "icon": "📍",
            "desc": "Kleines Nadelkissen",
        },
        {"name": "Duftkissen", "width": 50, "height": 50, "icon": "🌸", "desc": "Lavendelkissen"},
        {
            "name": "Sofakissen Klein",
            "width": 100,
            "height": 100,
            "icon": "🛋️",
            "desc": "30×30 cm Kissen",
        },
        {
            "name": "Sofakissen Groß",
            "width": 140,
            "height": 140,
            "icon": "🛏️",
            "desc": "40×40 cm Kissen",
        },
    ],
    "Accessoires": [
        {
            "name": "Schlüsselanhänger",
            "width": 20,
            "height": 30,
            "icon": "🔑",
            "desc": "Mini-Anhänger",
        },
        {
            "name": "Taschenspiegel",
            "width": 35,
            "height": 35,
            "icon": "🪞",
            "desc": "Rund, für Spiegel",
        },
        {
            "name": "Brillenetui",
            "width": 35,
            "height": 70,
            "icon": "👓",
            "desc": "Für Brillenetui-Einsatz",
        },
        {
            "name": "Handytasche",
            "width": 40,
            "height": 80,
            "icon": "📱",
            "desc": "Smartphone-Hülle",
        },
        {
            "name": "Geldbörse",
            "width": 50,
            "height": 40,
            "icon": "👛",
            "desc": "Für Geldbörsen-Einsatz",
        },
    ],
    "Weihnachten": [
        {
            "name": "Baumschmuck Klein",
            "width": 25,
            "height": 25,
            "icon": "🎄",
            "desc": "Kleiner Anhänger",
        },
        {
            "name": "Baumschmuck Groß",
            "width": 40,
            "height": 50,
            "icon": "⭐",
            "desc": "Größerer Schmuck",
        },
        {"name": "Nikolausstiefel", "width": 60, "height": 80, "icon": "🥾", "desc": "Stiefelform"},
        {"name": "Adventskalender", "width": 120, "height": 150, "icon": "📅", "desc": "24 Felder"},
    ],
}


class TemplatePreview(QWidget):
    """Vorschau für Template-Größe."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._width = 50
        self._height = 50
        self._name = "Benutzerdefiniert"
        self.setMinimumSize(200, 200)

    def set_size(self, width: int, height: int, name: str = "") -> None:
        self._width = width
        self._height = height
        self._name = name or f"{width}×{height}"
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Hintergrund
        painter.fillRect(self.rect(), QColor(THEME.bg_dark))

        # Verfügbare Fläche — Text-Block braucht: Name (20) + Spacing (4) +
        # Sub-Text (16) + Bottom-Padding (8) = 48 px
        margin = 16
        text_block_h = 48
        avail_w = self.width() - 2 * margin
        avail_h = self.height() - 2 * margin - text_block_h

        # Skalierung berechnen
        scale = min(avail_w / self._width, avail_h / self._height)

        # Rechteck-Größe
        rect_w = int(self._width * scale)
        rect_h = int(self._height * scale)

        # Zentrieren (vertikal: oberhalb des Text-Blocks)
        x = (self.width() - rect_w) // 2
        y = margin + (avail_h - rect_h) // 2

        # Schatten
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 50))
        painter.drawRect(x + 4, y + 4, rect_w, rect_h)

        # Rechteck
        painter.setBrush(QColor(THEME.bg_light))
        painter.setPen(QPen(QColor(THEME.accent_primary), 2))
        painter.drawRect(x, y, rect_w, rect_h)

        # Raster andeuten
        painter.setPen(QPen(QColor(THEME.border_dark), 1, Qt.PenStyle.DotLine))

        # Horizontale Linien (10er-Raster)
        cells_shown = min(10, self._height // 10)
        if cells_shown > 0:
            cell_h = rect_h / cells_shown
            for i in range(1, cells_shown):
                ly = y + int(i * cell_h)
                painter.drawLine(x, ly, x + rect_w, ly)

        # Vertikale Linien
        cells_shown_w = min(10, self._width // 10)
        if cells_shown_w > 0:
            cell_w = rect_w / cells_shown_w
            for i in range(1, cells_shown_w):
                lx = x + int(i * cell_w)
                painter.drawLine(lx, y, lx, y + rect_h)

        # Text-Block am unteren Rand — beide Zeilen passen sicher rein,
        # weil _avail_h_ oben um text_block_h reduziert wurde.
        # Layout: Name (20px) → Spacing → Sub-Text (16px) → 8px Bottom-Padding
        bottom_pad = 8
        sub_h = 16
        name_h = 20
        sub_y = self.height() - bottom_pad - sub_h
        name_y = sub_y - name_h

        painter.setPen(QColor(THEME.text_primary))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.drawText(0, name_y, self.width(), name_h, Qt.AlignmentFlag.AlignCenter, self._name)

        painter.setPen(QColor(THEME.text_muted))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(
            0,
            sub_y,
            self.width(),
            sub_h,
            Qt.AlignmentFlag.AlignCenter,
            f"{self._width} × {self._height} Stiche",
        )


class TemplateCard(QFrame):
    """Karte für ein einzelnes Template."""

    clicked = Signal(dict)

    def __init__(self, template: dict, parent=None) -> None:
        super().__init__(parent)
        self._template = template
        self._selected = False

        self.setFixedSize(140, 90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()
        self._update_style()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)

        # Icon + Name
        header = QHBoxLayout()

        icon = QLabel(self._template.get("icon", "📄"))
        icon.setStyleSheet("font-size: 20px;")
        header.addWidget(icon)

        name = QLabel(self._template["name"])
        name.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {THEME.text_primary};")
        name.setWordWrap(True)
        header.addWidget(name, 1)

        layout.addLayout(header)

        # Größe
        size_label = QLabel(f"{self._template['width']} × {self._template['height']}")
        size_label.setStyleSheet(
            f"font-size: 10px; color: {THEME.accent_primary}; font-weight: bold;"
        )
        layout.addWidget(size_label)

        # Beschreibung
        desc = QLabel(self._template.get("desc", ""))
        desc.setStyleSheet(f"font-size: 9px; color: {THEME.text_muted};")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addStretch()

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, value: bool) -> None:
        self._selected = value
        self._update_style()

    def _update_style(self) -> None:
        if self._selected:
            self.setStyleSheet(f"""
                TemplateCard {{
                    background: {THEME.bg_light};
                    border: 2px solid {THEME.accent_primary};
                    border-radius: 8px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                TemplateCard {{
                    background: {THEME.bg_medium};
                    border: 1px solid {THEME.border_dark};
                    border-radius: 8px;
                }}
                TemplateCard:hover {{
                    background: {THEME.bg_light};
                    border: 1px solid {THEME.accent_secondary};
                }}
            """)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._template)


class NewProjectDialog(QDialog):
    """Dialog zum Erstellen eines neuen Projekts mit Templates."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("Neues Projekt"))
        self.setMinimumSize(*UI_CONFIG.dialog_min_large)

        self._selected_template: dict | None = None
        self._template_cards: list[TemplateCard] = []

        self._setup_ui()
        self._apply_styles()

        # Standard: Benutzerdefiniert
        self._on_custom_selected()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # Linke Seite: Templates
        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)

        # Kategorie-Tabs als Radio-Buttons
        category_group = QGroupBox(t("Kategorie"))
        category_layout = QVBoxLayout(category_group)

        self._category_buttons = QButtonGroup(self)

        # "Benutzerdefiniert" zuerst
        custom_btn = QRadioButton(t("✏️ Benutzerdefiniert"))
        custom_btn.setChecked(True)
        self._category_buttons.addButton(custom_btn, 0)
        category_layout.addWidget(custom_btn)

        # Eigene Templates (ID = 1)
        user_btn = QRadioButton(t("⭐ Eigene Templates"))
        self._category_buttons.addButton(user_btn, 1)
        category_layout.addWidget(user_btn)

        # Trennlinie
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {THEME.border_dark};")
        category_layout.addWidget(sep)

        # Kategorien (IDs ab 2)
        for i, category in enumerate(TEMPLATES.keys(), 2):
            btn = QRadioButton(t(category))
            self._category_buttons.addButton(btn, i)
            category_layout.addWidget(btn)

        self._category_buttons.idClicked.connect(self._on_category_changed)

        left_panel.addWidget(category_group)

        # Template-Grid
        self._template_scroll = QScrollArea()
        self._template_scroll.setWidgetResizable(True)
        self._template_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._template_scroll.setMinimumWidth(320)

        self._template_container = QWidget()
        self._template_layout = QGridLayout(self._template_container)
        self._template_layout.setSpacing(8)
        self._template_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self._template_scroll.setWidget(self._template_container)
        left_panel.addWidget(self._template_scroll, 1)

        layout.addLayout(left_panel, 1)

        # Rechte Seite: Einstellungen + Vorschau
        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)

        # Größen-Einstellung
        size_group = QGroupBox(t("Größe"))
        size_layout = QGridLayout(size_group)

        # Diamond-Painting-Preset: liefert direkt eine sinnvolle Drill-Zahl
        # für ein bestimmtes DIN-Format bei 2.5mm Pitch. Wer den Eintrag
        # wählt, bekommt automatisch DP-Modus + die passende Drill-Anzahl.
        size_layout.addWidget(QLabel(t("DP-Preset:")), 0, 0)
        self._dp_preset_combo = QComboBox()
        self._dp_preset_combo.setToolTip(
            t(
                "Vorgefertigte Diamond-Painting-Größen, die 1:1 auf das "
                "jeweilige DIN-Format passen (bei 2.5mm Drill-Pitch)."
            )
        )
        # (Label, width, height, ist_dp)
        # None-Eintrag für "Stick-Modus / freie Wahl" — Default.
        self._DP_PRESETS = [
            ("— Keine Auswahl (eigene Werte) —", None, None, False),
            ("DP A4 quadratisch (60×60 = 15×15 cm)", 60, 60, True),
            ("DP A4 hoch (60×80 = 15×20 cm)", 60, 80, True),
            ("DP A4 quer (80×60 = 20×15 cm)", 80, 60, True),
            ("DP A3 (100×100 = 25×25 cm)", 100, 100, True),
            ("DP A3 quer (140×100 = 35×25 cm)", 140, 100, True),
            ("DP A2 (150×150 = 38×38 cm)", 150, 150, True),
            ("DP A2 quer (200×150 = 50×38 cm)", 200, 150, True),
            ("DP A1 (200×200 = 50×50 cm)", 200, 200, True),
            ("DP A1 quer (280×200 = 70×50 cm)", 280, 200, True),
            ("DP A0 (300×300 = 75×75 cm)", 300, 300, True),
            ("DP Gross (400×400 = 100×100 cm)", 400, 400, True),
        ]
        for label, _w, _h, _dp in self._DP_PRESETS:
            self._dp_preset_combo.addItem(label)
        self._dp_preset_combo.currentIndexChanged.connect(self._on_dp_preset_changed)
        size_layout.addWidget(self._dp_preset_combo, 0, 1)

        size_layout.addWidget(QLabel(t("Breite:")), 1, 0)
        self._width_spin = QSpinBox()
        self._width_spin.setRange(10, MAX_PATTERN_SIZE)
        self._width_spin.setValue(50)
        self._width_spin.setSuffix(t(" Stiche"))
        self._width_spin.valueChanged.connect(self._update_preview)
        size_layout.addWidget(self._width_spin, 1, 1)

        size_layout.addWidget(QLabel(t("Höhe:")), 2, 0)
        self._height_spin = QSpinBox()
        self._height_spin.setRange(10, MAX_PATTERN_SIZE)
        self._height_spin.setValue(50)
        self._height_spin.setSuffix(t(" Stiche"))
        self._height_spin.valueChanged.connect(self._update_preview)
        size_layout.addWidget(self._height_spin, 2, 1)

        right_panel.addWidget(size_group)

        # Stoff-Auswahl
        fabric_group = QGroupBox(t("Stoff"))
        fabric_layout = QHBoxLayout(fabric_group)

        fabric_layout.addWidget(QLabel(t("Stoffart:")))
        self._fabric_combo = QComboBox()
        self._fabric_combo.addItems(
            [
                t("Aida 11 (4,3 St/cm)"),
                t("Aida 14 (5,5 St/cm)"),
                t("Aida 16 (6,3 St/cm)"),
                t("Aida 18 (7,1 St/cm)"),
                t("Evenweave 28 (11 St/cm)"),
                t("Leinen 32 (12,6 St/cm)"),
            ]
        )
        self._fabric_combo.setCurrentIndex(1)  # Aida 14 als Standard
        self._fabric_combo.currentIndexChanged.connect(self._update_size_info)
        fabric_layout.addWidget(self._fabric_combo, 1)

        right_panel.addWidget(fabric_group)

        # Größen-Info
        self._size_info = QLabel()
        self._size_info.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px; padding: 5px;")
        self._size_info.setWordWrap(True)
        right_panel.addWidget(self._size_info)

        # Vorschau
        preview_group = QGroupBox(t("Vorschau"))
        preview_layout = QVBoxLayout(preview_group)

        self._preview = TemplatePreview()
        preview_layout.addWidget(self._preview)

        right_panel.addWidget(preview_group, 1)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.reject)

        self._create_btn = QPushButton(t("Erstellen"))
        self._create_btn.setDefault(True)
        self._create_btn.clicked.connect(self.accept)
        # _apply_styles() setzt einen eigenen dialogweiten QPushButton-Stil,
        # der die globale :default-Hervorhebung überschreibt.
        self._create_btn.setStyleSheet(Styles.button_primary())
        button_box.addButton(self._create_btn, QDialogButtonBox.ButtonRole.AcceptRole)

        button_layout.addWidget(button_box)

        right_panel.addLayout(button_layout)

        layout.addLayout(right_panel, 1)

        self._update_size_info()

    def _apply_styles(self) -> None:
        self.setStyleSheet(f"""
            QDialog {{
                background: {THEME.bg_dark};
            }}
            QGroupBox {{
                font-weight: bold;
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark};
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QSpinBox, QComboBox {{
                background: {THEME.bg_medium};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
                padding: 5px;
            }}
            QRadioButton {{
                color: {THEME.text_primary};
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
            }}
            QPushButton {{
                background: {THEME.bg_medium};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
                padding: 8px 15px;
            }}
            QPushButton:hover {{
                background: {THEME.bg_light};
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
        """)

    def _on_category_changed(self, id: int) -> None:
        """Kategorie gewechselt."""
        # Alle Template-Cards entfernen
        for card in self._template_cards:
            card.deleteLater()
        self._template_cards.clear()

        # Layout leeren
        while self._template_layout.count():
            item = self._template_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if id == 0:
            # Benutzerdefiniert
            self._on_custom_selected()
            return

        if id == 1:
            # Eigene Templates
            self._on_user_templates_selected()
            return

        # Templates der Kategorie anzeigen (IDs ab 2)
        category = list(TEMPLATES.keys())[id - 2]
        templates = TEMPLATES[category]

        for i, template in enumerate(templates):
            card = TemplateCard(template)
            card.clicked.connect(self._on_template_selected)
            self._template_cards.append(card)

            row = i // 2
            col = i % 2
            self._template_layout.addWidget(card, row, col)

        # Erstes Template auswählen
        if self._template_cards:
            self._template_cards[0].selected = True
            self._on_template_selected(templates[0])

        self._width_spin.setEnabled(False)
        self._height_spin.setEnabled(False)

    def _on_user_templates_selected(self) -> None:
        """Eigene Templates ausgewählt."""
        user_templates = load_user_templates()

        if not user_templates:
            # Keine eigenen Templates vorhanden
            info = QLabel(
                t(
                    "Noch keine eigenen Templates vorhanden.\n\n"
                    "Erstellen Sie ein Projekt und speichern Sie es\n"
                    "über Datei → Als Template speichern..."
                )
            )
            info.setWordWrap(True)
            info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            info.setStyleSheet(f"color: {THEME.text_muted}; padding: 20px;")
            self._template_layout.addWidget(info, 0, 0, 1, 2)

            self._selected_template = None
            self._width_spin.setEnabled(True)
            self._height_spin.setEnabled(True)
            self._update_preview()
            return

        # User-Templates als dict konvertieren und anzeigen
        for i, ut in enumerate(user_templates):
            template = {
                "name": ut.name,
                "width": ut.width,
                "height": ut.height,
                "icon": "⭐",
                "desc": ut.description or f"{ut.category}",
                "fabric_count": ut.fabric_count,
            }

            card = TemplateCard(template)
            card.clicked.connect(self._on_template_selected)
            self._template_cards.append(card)

            row = i // 2
            col = i % 2
            self._template_layout.addWidget(card, row, col)

        # Erstes Template auswählen
        if self._template_cards:
            self._template_cards[0].selected = True
            first_ut = user_templates[0]
            first_template = {
                "name": first_ut.name,
                "width": first_ut.width,
                "height": first_ut.height,
                "icon": "⭐",
                "desc": first_ut.description or "",
                "fabric_count": first_ut.fabric_count,
            }
            self._on_template_selected(first_template)

        self._width_spin.setEnabled(False)
        self._height_spin.setEnabled(False)

    def _on_custom_selected(self) -> None:
        """Benutzerdefiniert ausgewählt."""
        self._selected_template = None
        self._width_spin.setEnabled(True)
        self._height_spin.setEnabled(True)

        # Info-Label
        info = QLabel(
            t(
                "Geben Sie die gewünschte Größe ein oder wählen Sie eine Kategorie für vorgefertigte Templates."
            )
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {THEME.text_muted}; padding: 20px;")
        self._template_layout.addWidget(info, 0, 0, 1, 2)

        self._update_preview()

    def _on_template_selected(self, template: dict) -> None:
        """Template ausgewählt."""
        self._selected_template = template

        # Alle abwählen, dann dieses auswählen
        for card in self._template_cards:
            card.selected = card._template == template

        # Größe setzen
        self._width_spin.setValue(template["width"])
        self._height_spin.setValue(template["height"])

        self._update_preview()

    def _update_preview(self) -> None:
        """Vorschau aktualisieren."""
        name = ""
        if self._selected_template:
            name = self._selected_template["name"]

        self._preview.set_size(self._width_spin.value(), self._height_spin.value(), name)
        self._update_size_info()

    def _update_size_info(self) -> None:
        """Größen-Info aktualisieren."""
        fabric_counts = COMMON_FABRIC_COUNTS
        fabric_count = fabric_counts[self._fabric_combo.currentIndex()]

        # Berechnung der physischen Größe
        stitches_per_cm = fabric_count / 2.54
        width_cm = self._width_spin.value() / stitches_per_cm
        height_cm = self._height_spin.value() / stitches_per_cm

        total_stitches = self._width_spin.value() * self._height_spin.value()

        self._size_info.setText(
            f"📐 Fertige Größe: {width_cm:.1f} × {height_cm:.1f} cm\n"
            f"🔢 Max. Stiche: {total_stitches:,}\n"
            f"🧵 Stoff: {fabric_count} Stiche/Zoll"
        )

    def _on_dp_preset_changed(self, index: int) -> None:
        """DP-Preset gewählt → Breite/Höhe setzen + Modus markieren."""
        if index < 0 or index >= len(self._DP_PRESETS):
            return
        label, w, h, is_dp = self._DP_PRESETS[index]
        if w is None or h is None:
            # "Keine Auswahl" — Spinner-Werte unangetastet lassen
            self._dp_mode_selected = False
            return
        # Verhindere, dass valueChanged das Preset zurücksetzt während wir
        # setzen — kurz die Signale blockieren.
        self._width_spin.blockSignals(True)
        self._height_spin.blockSignals(True)
        self._width_spin.setValue(w)
        self._height_spin.setValue(h)
        self._width_spin.blockSignals(False)
        self._height_spin.blockSignals(False)
        self._dp_mode_selected = is_dp
        # Vorschau einmal aktualisieren
        self._update_preview()
        self._update_size_info()

    def get_settings(self) -> dict:
        """Gibt die gewählten Einstellungen zurück."""
        fabric_counts = COMMON_FABRIC_COUNTS

        return {
            "width": self._width_spin.value(),
            "height": self._height_spin.value(),
            "fabric_count": fabric_counts[self._fabric_combo.currentIndex()],
            "template_name": self._selected_template["name"] if self._selected_template else None,
            # True wenn ein DP-Preset gewählt wurde — der File-Handler
            # setzt entsprechend Pattern.mode='diamond' und fabric_count=10
            # (Standard 2.5mm Drill-Pitch).
            "dp_mode": getattr(self, "_dp_mode_selected", False),
        }
