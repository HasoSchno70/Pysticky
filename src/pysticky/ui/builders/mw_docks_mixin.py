"""
Dock-Widget-Builder-Mixin für MainWindow.

Enthält die Erstellung der Dock-Widgets.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget

from ...core.i18n import t

if TYPE_CHECKING:
    from ..main_window import MainWindow


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
        layer_dock = self._create_dock(t("Ebenen"), self.layer_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, layer_dock)

        # Paletten-Panel (rechts) — Dock-Titel wird beim Modus-Wechsel
        # angepasst (siehe view_handlers._apply_pattern_mode).
        self.palette_panel = PalettePanel(self)
        palette_dock = self._create_dock(t("Garnpaletten"), self.palette_panel)
        self.palette_dock = palette_dock  # damit der View-Handler den Titel umschreiben kann
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, palette_dock)

        # Info-Panel (rechts, getabbed mit Palette)
        self.info_panel = InfoPanel(self)
        info_dock = self._create_dock(t("Information"), self.info_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, info_dock)
        self.tabifyDockWidget(palette_dock, info_dock)
        palette_dock.raise_()

        # Text-Options-Panel (links, versteckt)
        self.text_options_panel = TextOptionsPanel(self)
        self.text_options_dock = self._create_dock(t("Text-Optionen"), self.text_options_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.text_options_dock)
        self.text_options_dock.setVisible(False)

        # Gradient-Options-Panel (links, versteckt)
        self.gradient_options_panel = GradientOptionsPanel(self)
        self.gradient_options_dock = self._create_dock(
            t("Farbverlauf"), self.gradient_options_panel
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.gradient_options_dock)
        self.gradient_options_dock.setVisible(False)

        # Minimap-Panel (links)
        self.minimap_panel = MinimapPanel(self)
        minimap_dock = self._create_dock(t("Übersicht"), self.minimap_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, minimap_dock)

        # Muster-Kacheln Panel (rechts, getabbed)
        self.tile_preview_panel = TilePreviewPanel(self)
        tile_dock = self._create_dock(t("Muster-Kacheln"), self.tile_preview_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, tile_dock)
        self.tabifyDockWidget(info_dock, tile_dock)

        # Hinweis: Stoff-Vorschau-Panel entfernt — die Funktionalitaet steckt
        # vollstaendig im Mustervorschau-Dialog (Ansicht → Mustervorschau).

        # Fortschritts-Panel (rechts, getabbed) — im DP-Modus ausgeblendet,
        # weil Diamond-Painting keinen etablierten "schon-erledigt"-Workflow
        # wie Kreuzstich hat (Drills werden zonenweise platziert, nicht
        # einzeln abgehakt).
        self.progress_panel = ProgressPanel(self)
        progress_dock = self._create_dock(t("Fortschritt"), self.progress_panel)
        self.progress_dock = progress_dock
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, progress_dock)
        self.tabifyDockWidget(tile_dock, progress_dock)

        # Größen anpassen
        self.resizeDocks([layer_dock], [220], Qt.Orientation.Horizontal)
        self.resizeDocks([palette_dock], [400], Qt.Orientation.Horizontal)

    def _create_dock(self, title: str, widget) -> QDockWidget:
        """Erstellt ein Dock-Widget mit Standard-Einstellungen."""
        dock = QDockWidget(title, self)
        dock.setWidget(widget)
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        return dock
