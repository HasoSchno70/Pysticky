"""
Dock-Widget-Builder-Mixin für MainWindow.

Enthält die Erstellung der Dock-Widgets.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QDockWidget

from ...core.i18n import t

if TYPE_CHECKING:
    from ..main_window import MainWindow


def _make_dot_icon(color_hex: str, size: int = 14) -> QIcon:
    """Erstellt ein kleines farbiges Kreis-Icon (für Dock-Tab-Markierungen)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color_hex))
    painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.end()
    return QIcon(pixmap)


class DockBuilderMixin:
    """Mixin für Dock-Widget-Erstellung."""

    def _create_dock_widgets(self: "MainWindow") -> None:
        """Erstellt alle Dock-Widgets."""
        from ..panels.gradient_options_panel import GradientOptionsPanel
        from ..panels.info_panel import InfoPanel
        from ..panels.layer_panel import LayerPanel
        from ..panels.palette_panel import PalettePanel
        from ..panels.progress_panel import ProgressPanel
        from ..panels.text_options_panel import TextOptionsPanel
        from ..panels.tile_preview_panel import TilePreviewPanel
        from ..widgets.minimap import MinimapPanel

        # Layer-Panel (links)
        self.layer_panel = LayerPanel(self)
        layer_dock = self._create_dock(t("Ebenen"), self.layer_panel, "dock_layers")
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, layer_dock)

        # Paletten-Panel (rechts) — Dock-Titel wird beim Modus-Wechsel
        # angepasst (siehe view_handlers._apply_pattern_mode).
        self.palette_panel = PalettePanel(self)
        palette_dock = self._create_dock(t("Garnpaletten"), self.palette_panel, "dock_palette")
        self.palette_dock = palette_dock  # damit der View-Handler den Titel umschreiben kann
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, palette_dock)

        # Info-Panel (rechts, getabbed mit Palette)
        self.info_panel = InfoPanel(self)
        info_dock = self._create_dock(t("Information"), self.info_panel, "dock_info")
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, info_dock)
        self.tabifyDockWidget(palette_dock, info_dock)
        palette_dock.raise_()

        # Text-Options-Panel (links, versteckt)
        self.text_options_panel = TextOptionsPanel(self)
        self.text_options_dock = self._create_dock(
            t("Text-Optionen"), self.text_options_panel, "dock_text_options"
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.text_options_dock)
        self.text_options_dock.setVisible(False)

        # Gradient-Options-Panel (links, versteckt)
        self.gradient_options_panel = GradientOptionsPanel(self)
        self.gradient_options_dock = self._create_dock(
            t("Farbverlauf"), self.gradient_options_panel, "dock_gradient_options"
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.gradient_options_dock)
        self.gradient_options_dock.setVisible(False)

        # Minimap-Panel (links)
        self.minimap_panel = MinimapPanel(self)
        minimap_dock = self._create_dock(t("Übersicht"), self.minimap_panel, "dock_minimap")
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, minimap_dock)

        # Muster-Kacheln Panel (rechts, getabbed)
        self.tile_preview_panel = TilePreviewPanel(self)
        tile_dock = self._create_dock(
            t("Muster-Kacheln"), self.tile_preview_panel, "dock_tile_preview"
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, tile_dock)
        self.tabifyDockWidget(info_dock, tile_dock)

        # Hinweis: Stoff-Vorschau-Panel entfernt — die Funktionalität steckt
        # vollständig im Mustervorschau-Dialog (Ansicht → Mustervorschau).

        # Fortschritts-Panel (rechts, getabbed) — im DP-Modus ausgeblendet,
        # weil Diamond-Painting keinen etablierten "schon-erledigt"-Workflow
        # wie Kreuzstich hat (Drills werden zonenweise platziert, nicht
        # einzeln abgehakt).
        self.progress_panel = ProgressPanel(self)
        progress_dock = self._create_dock(t("Fortschritt"), self.progress_panel, "dock_progress")
        self.progress_dock = progress_dock
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, progress_dock)
        self.tabifyDockWidget(tile_dock, progress_dock)

        # Größen anpassen
        self.resizeDocks([layer_dock], [220], Qt.Orientation.Horizontal)
        self.resizeDocks([palette_dock], [400], Qt.Orientation.Horizontal)

        # Rechts getabbte Docks bekommen je einen farbigen Tab-Punkt, damit
        # die Tabs sich unterscheiden lassen statt alle gleich grau zu wirken.
        self._dock_tab_widgets = {
            palette_dock: "accent_purple",
            info_dock: "info",
            tile_dock: "accent_secondary",
            progress_dock: "success",
        }
        self._apply_dock_tab_colors()

    def _apply_dock_tab_colors(self: "MainWindow") -> None:
        """Setzt/aktualisiert die farbigen Tab-Punkte (siehe _create_dock_widgets).

        Wird auch nach einem Theme-Wechsel erneut aufgerufen, damit die
        Farben zum jeweils aktiven Theme passen (siehe _reapply_all_widget_styles).
        """
        from PySide6.QtCore import QSize
        from PySide6.QtWidgets import QTabBar

        from ..styles import THEME

        mapping = getattr(self, "_dock_tab_widgets", None)
        if not mapping:
            return
        for dock, color_attr in mapping.items():
            color_hex = getattr(THEME, color_attr)
            dock.setWindowIcon(_make_dot_icon(color_hex))

        for tab_bar in self.findChildren(QTabBar):
            if tab_bar.iconSize().width() < 14:
                tab_bar.setIconSize(QSize(14, 14))

    def _create_dock(self, title: str, widget, object_name: str) -> QDockWidget:
        """Erstellt ein Dock-Widget mit Standard-Einstellungen.

        Args:
            object_name: stabiler, sprachunabhaengiger Schluessel (NICHT der
                uebersetzte Titel!). QMainWindow.saveState()/restoreState()
                identifiziert Docks ueber objectName() -- ohne diesen Aufruf
                blieb jedes Dock namenlos und restoreState() stellte lautlos
                GAR NICHTS wieder her (kein Fehler, einfach No-Op). Betraf
                sowohl den "Dock-Layout beim Start wiederherstellen"-Pfad
                (main_window.py) als auch WorkspaceProfileManager (Runde 12) --
                dessen Kernfunktion war dadurch faktisch nie wirksam.
        """
        dock = QDockWidget(title, self)
        dock.setObjectName(object_name)
        dock.setWidget(widget)
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        return dock
