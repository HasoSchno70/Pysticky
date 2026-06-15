"""
Dialog zum Erzeugen von Tweed-Blends aus zwei Threads.

Profis kombinieren z.B. 1 Strang DMC 310 + 1 Strang DMC 745 in einer
Nadel, um "Salt&Pepper"- oder "Tweed"-Effekte zu erzeugen. Dieser Dialog
laesst den User zwei Threads aus seinen geladenen Paletten auswaehlen,
ein Strang-Verhaeltnis festlegen, und das Ergebnis als neuen Eintrag in
die Pattern-Palette einfuegen.

Die Mischfarbe wird perzeptuell im CIE-Lab-Raum berechnet — entspricht
also dem, was der Stickerin am Ende auf dem Stoff begegnet.
"""

from typing import Optional

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from ...core.palette import get_palette_manager
from ...core.thread import Thread


class BlendThreadsDialog(QDialog):
    """Dialog zur Erzeugung eines Tweed-Blends aus zwei Threads."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tweed-Blend erzeugen")
        self.setMinimumWidth(440)
        self._result_thread: Optional[Thread] = None

        self._setup_ui()
        self._populate_palettes()
        self._update_preview()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(
            "Kombiniere zwei Garne zu einem Tweed-Effekt. Beispiel: 1 Strang DMC 310 "
            "(schwarz) + 1 Strang DMC 745 (creme) ergibt einen warmen "
            "Salt&Pepper-Ton. Die Mischfarbe wird perzeptuell berechnet (CIE-Lab)."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Komponente 1
        form = QFormLayout()

        self.combo_palette_a = QComboBox()
        self.combo_thread_a = QComboBox()
        self.combo_thread_a.setMinimumWidth(220)
        self.spin_strands_a = QSpinBox()
        self.spin_strands_a.setRange(1, 6)
        self.spin_strands_a.setValue(1)

        form.addRow("Palette A:", self.combo_palette_a)
        form.addRow("Garn A:", self.combo_thread_a)
        form.addRow("Straenge A:", self.spin_strands_a)

        # Komponente 2
        self.combo_palette_b = QComboBox()
        self.combo_thread_b = QComboBox()
        self.combo_thread_b.setMinimumWidth(220)
        self.spin_strands_b = QSpinBox()
        self.spin_strands_b.setRange(1, 6)
        self.spin_strands_b.setValue(1)

        form.addRow("Palette B:", self.combo_palette_b)
        form.addRow("Garn B:", self.combo_thread_b)
        form.addRow("Straenge B:", self.spin_strands_b)

        layout.addLayout(form)

        # Vorschau
        preview_row = QHBoxLayout()
        preview_label = QLabel("Vorschau:")
        self.preview_swatch = QFrame()
        self.preview_swatch.setFrameShape(QFrame.Shape.Box)
        self.preview_swatch.setFixedSize(64, 64)
        self.preview_swatch.setAutoFillBackground(True)
        self.preview_text = QLabel("")
        self.preview_text.setWordWrap(True)
        preview_row.addWidget(preview_label)
        preview_row.addWidget(self.preview_swatch)
        preview_row.addWidget(self.preview_text, 1)
        layout.addLayout(preview_row)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Zum Pattern hinzufuegen")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Signals
        self.combo_palette_a.currentTextChanged.connect(
            lambda name: self._fill_threads(self.combo_thread_a, name)
        )
        self.combo_palette_b.currentTextChanged.connect(
            lambda name: self._fill_threads(self.combo_thread_b, name)
        )
        for sig in (
            self.combo_thread_a.currentIndexChanged,
            self.combo_thread_b.currentIndexChanged,
            self.spin_strands_a.valueChanged,
            self.spin_strands_b.valueChanged,
        ):
            sig.connect(self._update_preview)

    def _populate_palettes(self) -> None:
        pm = get_palette_manager()
        pm.load_all()
        # Bead-Paletten ausblenden — Tweed-Blends sind Garn-Mixes
        names = sorted(
            n
            for n in pm.available_palettes
            if not (pm.get_palette(n) and pm.get_palette(n).is_beads)
        )
        for combo in (self.combo_palette_a, self.combo_palette_b):
            combo.clear()
            combo.addItems(names)
        # Default: beide auf DMC wenn vorhanden, sonst erste verfuegbare
        if "DMC" in names:
            self.combo_palette_a.setCurrentText("DMC")
            self.combo_palette_b.setCurrentText("DMC")
        self._fill_threads(self.combo_thread_a, self.combo_palette_a.currentText())
        self._fill_threads(self.combo_thread_b, self.combo_palette_b.currentText())

    def _fill_threads(self, combo: QComboBox, palette_name: str) -> None:
        pm = get_palette_manager()
        palette = pm.get_palette(palette_name)
        combo.clear()
        if palette is None:
            return
        for thread in palette.threads:
            label = f"{thread.catalog_number or ''} — {thread.name}".strip(" —")
            combo.addItem(label, userData=thread)
        self._update_preview()

    def _selected_thread(self, combo: QComboBox) -> Optional[Thread]:
        idx = combo.currentIndex()
        if idx < 0:
            return None
        return combo.itemData(idx)

    def _update_preview(self) -> None:
        ta = self._selected_thread(self.combo_thread_a)
        tb = self._selected_thread(self.combo_thread_b)
        if ta is None or tb is None:
            self.preview_text.setText("(Beide Garne waehlen)")
            return

        try:
            blend = Thread.blend(
                [ta, tb],
                [self.spin_strands_a.value(), self.spin_strands_b.value()],
            )
        except ValueError as e:
            self.preview_text.setText(f"Fehler: {e}")
            return

        # Swatch einfaerben
        pal = self.preview_swatch.palette()
        pal.setColor(
            QPalette.ColorRole.Window,
            QColor(blend.color.r, blend.color.g, blend.color.b),
        )
        self.preview_swatch.setPalette(pal)

        self.preview_text.setText(
            f"<b>{blend.name}</b><br>"
            f"<span style='color:#666;'>Mischfarbe: {blend.color.to_hex()}</span>"
        )

    def _on_accept(self) -> None:
        ta = self._selected_thread(self.combo_thread_a)
        tb = self._selected_thread(self.combo_thread_b)
        if ta is None or tb is None:
            return
        try:
            self._result_thread = Thread.blend(
                [ta, tb],
                [self.spin_strands_a.value(), self.spin_strands_b.value()],
            )
        except ValueError:
            return
        self.accept()

    @property
    def result_thread(self) -> Optional[Thread]:
        """Liefert den erzeugten Blend-Thread oder None wenn abgebrochen."""
        return self._result_thread
