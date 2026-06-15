"""
Text-Optionen Panel für das Text-Werkzeug.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFontComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core.i18n import t
from ..styles import THEME, Styles


class TextOptionsPanel(QWidget):
    """Panel für Text-Werkzeug Optionen."""

    text_changed = Signal(str)
    font_changed = Signal(str)
    size_changed = Signal(int)
    bold_changed = Signal(bool)
    italic_changed = Signal(bool)
    confirm_clicked = Signal()
    cancel_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self._separators: list[QFrame] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header
        self._header = QLabel(t("TEXT-WERKZEUG"))
        self._header.setStyleSheet(Styles.section_header())
        layout.addWidget(self._header)

        layout.addWidget(self._create_separator())

        # Text-Eingabe
        self._text_label = QLabel(t("Text:"))
        self._text_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        layout.addWidget(self._text_label)

        self._text_input = QLineEdit()
        self._text_input.setPlaceholderText(t("Text eingeben..."))
        self._text_input.setStyleSheet(f"""
            QLineEdit {{
                background: {THEME.bg_dark};
                border: 1px solid {THEME.border_medium};
                border-radius: 4px;
                padding: 8px;
                color: {THEME.text_primary};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {THEME.accent_primary};
            }}
        """)
        self._text_input.textChanged.connect(self.text_changed.emit)
        layout.addWidget(self._text_input)

        layout.addWidget(self._create_separator())

        # Schriftart
        self._font_label = QLabel(t("Schriftart:"))
        self._font_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        layout.addWidget(self._font_label)

        self._font_combo = QFontComboBox()
        self._font_combo.setCurrentFont(QFont("Arial"))
        self._font_combo.setStyleSheet(f"""
            QFontComboBox {{
                background: {THEME.bg_dark};
                border: 1px solid {THEME.border_medium};
                border-radius: 4px;
                padding: 4px 8px;
                color: {THEME.text_primary};
            }}
            QFontComboBox:hover {{
                border-color: {THEME.accent_primary};
            }}
            QFontComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QFontComboBox QAbstractItemView {{
                background: {THEME.bg_dark};
                color: {THEME.text_primary};
                selection-background-color: {THEME.accent_primary};
            }}
        """)
        self._font_combo.currentFontChanged.connect(lambda f: self.font_changed.emit(f.family()))
        layout.addWidget(self._font_combo)

        # Größe
        size_layout = QHBoxLayout()

        self._size_label = QLabel(t("Größe:"))
        self._size_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        size_layout.addWidget(self._size_label)

        self._size_spin = QSpinBox()
        self._size_spin.setRange(6, 72)
        self._size_spin.setValue(12)
        self._size_spin.setSuffix(" px")
        self._size_spin.setStyleSheet(f"""
            QSpinBox {{
                background: {THEME.bg_dark};
                border: 1px solid {THEME.border_medium};
                border-radius: 4px;
                padding: 4px 8px;
                color: {THEME.text_primary};
                min-width: 70px;
            }}
            QSpinBox:hover {{
                border-color: {THEME.accent_primary};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background: {THEME.bg_light};
                border: none;
                width: 16px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background: {THEME.accent_primary};
            }}
        """)
        self._size_spin.valueChanged.connect(self.size_changed.emit)
        size_layout.addWidget(self._size_spin)

        size_layout.addStretch()
        layout.addLayout(size_layout)

        # Stil
        style_layout = QHBoxLayout()

        self._bold_check = QCheckBox(t("Fett"))
        self._bold_check.setStyleSheet(self._checkbox_style())
        self._bold_check.toggled.connect(self.bold_changed.emit)
        style_layout.addWidget(self._bold_check)

        self._italic_check = QCheckBox(t("Kursiv"))
        self._italic_check.setStyleSheet(self._checkbox_style())
        self._italic_check.toggled.connect(self.italic_changed.emit)
        style_layout.addWidget(self._italic_check)

        style_layout.addStretch()
        layout.addLayout(style_layout)

        layout.addWidget(self._create_separator())

        # Vorschau
        self._preview_label_header = QLabel(t("Vorschau:"))
        self._preview_label_header.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        layout.addWidget(self._preview_label_header)

        self._preview_label = QLabel("")
        self._preview_label.setMinimumHeight(40)
        self._preview_label.setStyleSheet(f"""
            background: {THEME.bg_dark};
            border: 1px solid {THEME.border_medium};
            border-radius: 4px;
            padding: 8px;
            color: {THEME.text_primary};
        """)
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._preview_label)

        # Verbindungen für Vorschau-Update
        self._text_input.textChanged.connect(self._update_preview)
        self._font_combo.currentFontChanged.connect(self._update_preview)
        self._size_spin.valueChanged.connect(self._update_preview)
        self._bold_check.toggled.connect(self._update_preview)
        self._italic_check.toggled.connect(self._update_preview)

        layout.addWidget(self._create_separator())

        # Buttons
        btn_layout = QHBoxLayout()

        self._confirm_btn = QPushButton("✓ " + t("Platzieren"))
        self._confirm_btn.setStyleSheet(Styles.button_primary())
        self._confirm_btn.clicked.connect(self.confirm_clicked.emit)
        btn_layout.addWidget(self._confirm_btn)

        self._cancel_btn = QPushButton("✕ " + t("Abbrechen"))
        self._cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {THEME.bg_light};
                border: 1px solid {THEME.error};
                border-radius: 4px;
                padding: 8px 16px;
                color: {THEME.text_primary};
            }}
            QPushButton:hover {{
                background: {THEME.bg_lighter};
            }}
            QPushButton:pressed {{
                background: {THEME.bg_dark};
            }}
        """)
        self._cancel_btn.clicked.connect(self.cancel_clicked.emit)
        btn_layout.addWidget(self._cancel_btn)

        layout.addLayout(btn_layout)

        # Hinweis
        self._hint = QLabel(
            t("Klicke auf Canvas um Text zu platzieren.\nEnter = Bestätigen, Esc = Abbrechen")
        )
        self._hint.setStyleSheet(
            f"color: {THEME.text_disabled}; font-size: 10px; font-style: italic;"
        )
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._hint)

        layout.addStretch()

        self.setStyleSheet(f"TextOptionsPanel {{ background: {THEME.bg_medium}; }}")

    def _apply_theme(self) -> None:
        """Re-applies all stylesheets for theme switching."""
        self.setStyleSheet(f"TextOptionsPanel {{ background: {THEME.bg_medium}; }}")
        self._header.setStyleSheet(Styles.section_header())
        self._text_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        self._text_input.setStyleSheet(f"""
            QLineEdit {{
                background: {THEME.bg_dark};
                border: 1px solid {THEME.border_medium};
                border-radius: 4px;
                padding: 8px;
                color: {THEME.text_primary};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {THEME.accent_primary};
            }}
        """)
        self._font_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        self._font_combo.setStyleSheet(f"""
            QFontComboBox {{
                background: {THEME.bg_dark};
                border: 1px solid {THEME.border_medium};
                border-radius: 4px;
                padding: 4px 8px;
                color: {THEME.text_primary};
            }}
            QFontComboBox:hover {{
                border-color: {THEME.accent_primary};
            }}
            QFontComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QFontComboBox QAbstractItemView {{
                background: {THEME.bg_dark};
                color: {THEME.text_primary};
                selection-background-color: {THEME.accent_primary};
            }}
        """)
        self._size_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        self._size_spin.setStyleSheet(f"""
            QSpinBox {{
                background: {THEME.bg_dark};
                border: 1px solid {THEME.border_medium};
                border-radius: 4px;
                padding: 4px 8px;
                color: {THEME.text_primary};
                min-width: 70px;
            }}
            QSpinBox:hover {{
                border-color: {THEME.accent_primary};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background: {THEME.bg_light};
                border: none;
                width: 16px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background: {THEME.accent_primary};
            }}
        """)
        self._bold_check.setStyleSheet(self._checkbox_style())
        self._italic_check.setStyleSheet(self._checkbox_style())
        self._preview_label_header.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        self._preview_label.setStyleSheet(f"""
            background: {THEME.bg_dark};
            border: 1px solid {THEME.border_medium};
            border-radius: 4px;
            padding: 8px;
            color: {THEME.text_primary};
        """)
        self._confirm_btn.setStyleSheet(Styles.button_primary())
        self._cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {THEME.bg_light};
                border: 1px solid {THEME.error};
                border-radius: 4px;
                padding: 8px 16px;
                color: {THEME.text_primary};
            }}
            QPushButton:hover {{
                background: {THEME.bg_lighter};
            }}
            QPushButton:pressed {{
                background: {THEME.bg_dark};
            }}
        """)
        self._hint.setStyleSheet(
            f"color: {THEME.text_disabled}; font-size: 10px; font-style: italic;"
        )
        for sep in self._separators:
            sep.setStyleSheet(f"background: {THEME.border_medium}; max-height: 1px;")

    def _create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {THEME.border_medium}; max-height: 1px;")
        self._separators.append(sep)
        return sep

    def _checkbox_style(self) -> str:
        return f"""
            QCheckBox {{
                color: {THEME.text_muted};
                font-size: 11px;
                spacing: 6px;
            }}
            QCheckBox:hover {{
                color: {THEME.text_secondary};
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {THEME.border_light};
                border-radius: 3px;
                background: {THEME.bg_dark};
            }}
            QCheckBox::indicator:checked {{
                background: {THEME.accent_primary};
                border-color: {THEME.accent_primary};
            }}
            QCheckBox::indicator:hover {{
                border-color: {THEME.accent_primary};
            }}
        """

    def _update_preview(self) -> None:
        text = self._text_input.text()
        if not text:
            self._preview_label.setText("")
            return

        font = QFont(self._font_combo.currentFont().family(), self._size_spin.value())
        font.setBold(self._bold_check.isChecked())
        font.setItalic(self._italic_check.isChecked())

        self._preview_label.setFont(font)
        self._preview_label.setText(text)

    @property
    def text(self) -> str:
        return self._text_input.text()

    @property
    def font_family(self) -> str:
        return self._font_combo.currentFont().family()

    @property
    def font_size(self) -> int:
        return self._size_spin.value()

    @property
    def bold(self) -> bool:
        return self._bold_check.isChecked()

    @property
    def italic(self) -> bool:
        return self._italic_check.isChecked()

    def clear(self) -> None:
        self._text_input.clear()

    def focus_text_input(self) -> None:
        self._text_input.setFocus()
        self._text_input.selectAll()
