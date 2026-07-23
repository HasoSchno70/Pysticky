"""
Übersicht-Tab für den Statistik-Dialog.
"""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from ....core.difficulty import compute_difficulty
from ....core.i18n import t
from ...color_utils import to_qcolor
from ...styles import THEME
from ...widgets.statistics_widgets import StatCard

if TYPE_CHECKING:
    from ....core import Pattern


class OverviewTab(QWidget):
    """Tab: Übersicht mit Statistik-Karten und Top-5-Farbverteilung."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Statistik-Karten
        cards_layout = QGridLayout()
        cards_layout.setSpacing(10)

        self._card_size = StatCard(t("Größe"), "- × -", "📐")
        cards_layout.addWidget(self._card_size, 0, 0)

        self._card_stitches = StatCard(t("Gesamtstiche"), "-", "🧵")
        cards_layout.addWidget(self._card_stitches, 0, 1)

        self._card_colors = StatCard(t("Farben"), "-", "🎨")
        cards_layout.addWidget(self._card_colors, 0, 2)

        self._card_backstitches = StatCard(t("Rückstiche"), "-", "↙️")
        cards_layout.addWidget(self._card_backstitches, 1, 0)

        self._card_coverage = StatCard(t("Abdeckung"), "-", "📊")
        cards_layout.addWidget(self._card_coverage, 1, 1)

        self._card_layers = StatCard(t("Ebenen"), "-", "🗂️")
        cards_layout.addWidget(self._card_layers, 1, 2)

        # Schwierigkeits-Karte mit Tooltip-Detail (Faktor-Aufschlüsselung)
        self._card_difficulty = StatCard(t("Schwierigkeit"), "-", "🎯")
        cards_layout.addWidget(self._card_difficulty, 2, 0, 1, 3)

        layout.addLayout(cards_layout)

        # Farbverteilung (Top 5)
        dist_group = QGroupBox(t("Top 5 Farben"))
        dist_layout = QVBoxLayout(dist_group)

        self._color_bars: list[tuple[QWidget, QLabel, QProgressBar]] = []
        for _ in range(5):
            row = QHBoxLayout()

            color_preview = QWidget()
            color_preview.setFixedSize(20, 20)
            row.addWidget(color_preview)

            name_label = QLabel("-")
            name_label.setMinimumWidth(150)
            row.addWidget(name_label)

            bar = QProgressBar()
            bar.setMaximum(100)
            bar.setTextVisible(True)
            bar.setFormat("%v%")
            row.addWidget(bar, 1)

            dist_layout.addLayout(row)
            self._color_bars.append((color_preview, name_label, bar))

        layout.addWidget(dist_group)
        layout.addStretch()

    def update_stats(self, pattern: "Pattern", stats: dict) -> None:
        """Befüllt die Übersichts-Karten und die Top-5-Farbverteilung."""
        self._card_size.set_value(f"{stats['width']} × {stats['height']}")

        # Stiche: Zeige zu stickende Stiche (ohne übersprungene)
        if stats.get("skipped_stitches", 0) > 0:
            self._card_stitches.set_value(f"{stats['stitches_to_do']:,}")
        else:
            self._card_stitches.set_value(f"{stats['total_stitches']:,}")

        # Farben: Zeige verwendete - übersprungene.
        #
        # Regression: der else-Zweig zeigte vorher stats["color_count"] --
        # das ist IMMER die volle Palettengroesse (len(color_entries)),
        # nicht die Anzahl tatsaechlich gemalter Farben. Ein Muster mit
        # ungenutzten Palettenfarben (z.B. manuell hinzugefuegt, nie
        # gemalt) zeigte dadurch eine zu hohe Zahl, sobald skipped_colors
        # zufaellig 0 war -- die angezeigte Bedeutung der Karte kippte
        # abhaengig von einem voellig unabhaengigen Flag. "used - skipped"
        # ist in BEIDEN Faellen korrekt (bei skipped==0 gilt ohnehin
        # used - skipped == used).
        used = stats["used_colors"]
        skipped = stats.get("skipped_colors", 0)
        if skipped > 0:
            self._card_colors.set_value(f"{used - skipped} (+{skipped} {t('übersp.')})")
        else:
            self._card_colors.set_value(str(used - skipped))

        self._card_backstitches.set_value(str(len(pattern.backstitches)))

        # Abdeckung berechnen -- covered_cells (Composite über alle Layer,
        # jede Zelle höchstens 1x gezählt) verwenden, NICHT total_stitches:
        # letzteres summiert absichtlich pro Layer (siehe get_statistics()-
        # Docstring) und zeigte bei mehreren übereinanderliegenden, voll
        # gefüllten Layern eine "Abdeckung" > 100% an.
        total_cells = stats["width"] * stats["height"]
        if total_cells > 0:
            coverage = (stats["covered_cells"] / total_cells) * 100
            self._card_coverage.set_value(f"{coverage:.1f}%")
        else:
            self._card_coverage.set_value("0%")

        self._card_layers.set_value(str(len(pattern.layer_stack)))

        # Schwierigkeit
        diff = compute_difficulty(pattern)
        self._card_difficulty.set_value(diff["level"])
        f = diff["factors"]
        d = diff["details"]
        tip = (
            f"Score: {diff['score']} / 12\n"
            f"  Farben: {f['colors']}/3 ({d['used_colors']} verwendet)\n"
            f"  Stiche: {f['size']}/3 ({d['stitches_to_do']:,} zu sticken)\n"
            f"  Sonderstiche: {f['special']}/3 "
            f"({d['special_ratio'] * 100:.1f}% Anteil)\n"
            f"  Backstitches: {f['backstitches']}/3 ({d['backstitches']} Linien)"
        )
        self._card_difficulty.setToolTip(tip)

        # Top 5 Farben (ohne übersprungene)
        entries = sorted(
            [e for e in pattern.color_entries if not e.skip_stitching],
            key=lambda e: e.stitch_count,
            reverse=True,
        )[:5]

        total = stats.get("stitches_to_do", stats["total_stitches"]) or 1
        for i, (widgets, entry) in enumerate(zip(self._color_bars, entries + [None] * 5)):
            color_widget, name_label, bar = widgets

            if i < len(entries) and entry:
                # Farbe setzen
                color = to_qcolor(entry.thread.color)
                color_widget.setStyleSheet(f"""
                    background: {color.name()};
                    border: 1px solid {THEME.border_light};
                    border-radius: 3px;
                """)

                name_label.setText(f"{entry.symbol} {entry.thread.name}")
                percent = int((entry.stitch_count / total) * 100)
                bar.setValue(percent)
                bar.setFormat(f"{entry.stitch_count:,} ({percent}%)")
            else:
                color_widget.setStyleSheet(f"background: {THEME.bg_medium}; border-radius: 3px;")
                name_label.setText("-")
                bar.setValue(0)
                bar.setFormat("")
