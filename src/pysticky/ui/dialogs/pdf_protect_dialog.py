"""
PDF-Schutz-Dialog.

Konfiguriert Passwort, Wasserzeichen und Druck-/Kopier-Berechtigungen
für den PDF-Export. Erscheint optional vor dem eigentlichen Export.
"""

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from ...core.i18n import t


class PdfProtectDialog(QDialog):
    """Dialog zur Konfiguration des PDF-Schutzes."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("PDF-Schutz"))
        self.setMinimumWidth(420)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        info = QLabel(
            t(
                "Schutz ist OPTIONAL — leere Felder = kein Schutz.\n"
                "Wasserzeichen wird gross diagonal auf jede Seite gezeichnet."
            )
        )
        info.setStyleSheet("color: #888; font-size: 11px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()

        self.edit_password = QLineEdit()
        self.edit_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_password.setPlaceholderText(t("(kein Passwort)"))
        form.addRow(t("Passwort:"), self.edit_password)

        self.edit_watermark = QLineEdit()
        self.edit_watermark.setPlaceholderText(t("(kein Wasserzeichen)"))
        form.addRow(t("Wasserzeichen:"), self.edit_watermark)

        self.chk_print = QCheckBox(t("Drucken erlauben"))
        self.chk_print.setChecked(True)
        form.addRow("", self.chk_print)

        self.chk_copy = QCheckBox(t("Kopieren erlauben"))
        self.chk_copy.setChecked(True)
        form.addRow("", self.chk_copy)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def password(self) -> str | None:
        return self.edit_password.text() or None

    @property
    def watermark(self) -> str | None:
        return self.edit_watermark.text().strip() or None

    @property
    def allow_printing(self) -> bool:
        return self.chk_print.isChecked()

    @property
    def allow_copying(self) -> bool:
        return self.chk_copy.isChecked()
