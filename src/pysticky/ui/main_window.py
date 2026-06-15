"""
Hauptfenster der Kreuzstich-Anwendung.

Handler-Mixins (ui/handlers/):
- FileHandlersMixin: Datei-Operationen (Neu, Öffnen, Speichern, Import, Drucken)
- ExportHandlersMixin: PDF/HTML/Bild-Export inkl. Hintergrund-Worker
- AutosaveHandlersMixin: Automatisches Speichern + Recovery beim Start
- EditHandlersMixin: Bearbeiten & Transformationen (Undo, Redo, Resize, Rotate, Flip)
- ViewHandlersMixin: Ansicht & Navigation (Zoom, Grid, Symbole, Minimap)
- SelectionHandlersMixin: Auswahl-Operationen (Copy, Cut, Paste, Delete, Fill)
- UndoHandlersMixin: Undo/Redo-Signalverarbeitung und Fortschritts-Handler
- PanelHandlersMixin: Panel/Color-Handler (Farbe, Palette, Layer, Pipette)
- ToolHandlersMixin: Werkzeug-Handler (Text, Gradient, Tool-Wechsel)
- MiscHandlersMixin: Layer, Recent Files, Templates, Settings, About

Builder-Mixins (ui/builders/):
- ActionsBuilderMixin: Action-Definitionen
- MenuBuilderMixin: Menü-Erstellung
- ToolbarBuilderMixin: Toolbar-Erstellung
- DockBuilderMixin: Dock-Widget-Erstellung
- SignalsConnectorMixin: Signal-Verbindungen
"""

from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..config import (
    APP_NAME,
    FILE_CONFIG,
    ORG_NAME,
    UI_CONFIG,
    UNDO_CONFIG,
)
from ..core import Pattern, Thread, UndoManager

# Builder-Mixins importieren
from .builders import (
    ActionsBuilderMixin,
    DockBuilderMixin,
    MenuBuilderMixin,
    SignalsConnectorMixin,
    ToolbarBuilderMixin,
)

# Handler-Mixins importieren
from .handlers import (
    AutosaveHandlersMixin,
    EditHandlersMixin,
    ExportHandlersMixin,
    FileHandlersMixin,
    MiscHandlersMixin,
    PanelHandlersMixin,
    SelectionHandlersMixin,
    ToolHandlersMixin,
    UndoHandlersMixin,
    ViewHandlersMixin,
)
from .notify_scope import NotifyScope  # noqa: E302 – re-export for backwards compat
from .widgets.canvas_container import CanvasContainer
from .widgets.color_bar import ColorBar
from .widgets.tool_bar import ToolBar


class MainWindow(
    QMainWindow,
    # Handler-Mixins
    FileHandlersMixin,
    ExportHandlersMixin,
    AutosaveHandlersMixin,
    EditHandlersMixin,
    ViewHandlersMixin,
    SelectionHandlersMixin,
    UndoHandlersMixin,
    PanelHandlersMixin,
    ToolHandlersMixin,
    MiscHandlersMixin,
    # Builder-Mixins
    ActionsBuilderMixin,
    MenuBuilderMixin,
    ToolbarBuilderMixin,
    DockBuilderMixin,
    SignalsConnectorMixin,
):
    """
    Hauptfenster der PySticky Kreuzstich-Anwendung.

    Die meiste Logik ist in Mixin-Klassen ausgelagert.
    Diese Klasse enthält nur:
    - Initialisierung und Setup
    - Status-Updates und Panel-Koordination
    - Pattern-Verwaltung
    - Events (Keyboard, Drag&Drop, Close)
    """

    def __init__(self) -> None:
        super().__init__()

        self.current_pattern: Pattern = Pattern()
        self.current_file: Path | None = None
        self._unsaved_changes: bool = False

        # Einstellungen (Namen aus config.py)
        self._settings = QSettings(ORG_NAME, APP_NAME)
        self._recent_files: list[str] = self._load_recent_files()
        self._autosave_interval: int = self._settings.value(
            "autosave_interval", FILE_CONFIG.autosave_interval_minutes, type=int
        )
        self._autosave_enabled: bool = self._settings.value("autosave_enabled", True, type=bool)

        # Autosave-Timer
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._on_autosave)
        if self._autosave_enabled and self._autosave_interval > 0:
            self._autosave_timer.start(self._autosave_interval * 60 * 1000)

        # Undo-System (max_history aus config.py)
        self.undo_manager = UndoManager(max_history=UNDO_CONFIG.max_history)
        self.undo_manager.set_pattern(self.current_pattern)

        # Gespeichertes Theme laden (vor UI-Aufbau)
        from .styles import set_theme

        saved_theme = self._settings.value("theme", "dark", type=str)
        set_theme(saved_theme)

        # UI Setup (Methoden aus Mixins)
        self._setup_window()
        self._create_actions()  # ActionsBuilderMixin
        self._create_menus()  # MenuBuilderMixin
        self._create_toolbar()  # ToolbarBuilderMixin
        self._create_central_widget()
        self._create_dock_widgets()  # DockBuilderMixin
        self._create_status_bar()
        self._connect_signals()  # SignalsConnectorMixin

        # Gespeichertes Dock-Layout wiederherstellen
        saved_state = self._settings.value("window/state")
        if saved_state is not None:
            self.restoreState(saved_state)

        # Persistente Canvas-Einstellungen initial anwenden
        self.canvas.show_fabric_texture = self._settings.value("fabric_texture", True, type=bool)

        self._update_title()
        self._update_status()
        self._update_undo_actions()

        # Start-Aktion aus Einstellungen ausführen (verzögert nach UI-Initialisierung)
        QTimer.singleShot(100, self._perform_start_action)

    # =========================================================================
    # Setup-Methoden
    # =========================================================================

    def _setup_window(self) -> None:
        """Grundlegende Fenstereinstellungen."""
        from ..core.i18n import t

        self.setWindowTitle(f"{APP_NAME} - {t('Kreuzstich')}")
        self.setMinimumSize(UI_CONFIG.min_window_width, UI_CONFIG.min_window_height)
        self.setAcceptDrops(True)

        # Window-Icon setzen
        icon_path = Path(__file__).parent.parent / "resources" / "icons" / "sticken.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Gespeicherte Fenstergeometrie wiederherstellen
        saved_geometry = self._settings.value("window/geometry")
        if saved_geometry is not None:
            self.restoreGeometry(saved_geometry)
        else:
            # Standard-Position und -Größe
            screen = self.screen().availableGeometry()
            width = min(UI_CONFIG.default_window_width, int(screen.width() * 0.92))
            height = min(UI_CONFIG.default_window_height, int(screen.height() * 0.92))
            self.resize(width, height)

            x = (screen.width() - width) // 2
            y = (screen.height() - height) // 2
            self.move(x, y)

    def _create_central_widget(self) -> None:
        """Erstellt das zentrale Widget mit Canvas und Werkzeugleiste."""
        central = QWidget()
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.tool_bar = ToolBar(self)
        main_layout.addWidget(self.tool_bar)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.canvas_container = CanvasContainer(self)
        self.canvas = self.canvas_container.canvas
        self.canvas.setObjectName("crossStitchCanvas")
        # Welcome-Widget-Signale an die existierenden Handler binden
        self.canvas_container.welcome_new_clicked.connect(self._on_welcome_new)
        self.canvas_container.welcome_open_clicked.connect(self._on_welcome_open)
        self.canvas_container.welcome_import_image_clicked.connect(self._on_welcome_import)
        self.canvas_container.welcome_demo_clicked.connect(self._on_open_demo)
        self.canvas_container.welcome_open_recent.connect(self._on_welcome_open_recent)
        right_layout.addWidget(self.canvas_container, 1)

        self.color_bar = ColorBar(self)
        right_layout.addWidget(self.color_bar)

        main_layout.addWidget(right_widget, 1)
        self.setCentralWidget(central)

    def _create_status_bar(self) -> None:
        """Erstellt die Statusleiste mit stabilen Label-Breiten + Farb-Pills."""
        from ..core.i18n import t
        from .widgets.zoom_slider import ZoomSlider

        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)

        # Pill-artiges Tool-Label mit Accent-Primary-Tint
        self.label_tool = QLabel("🛠 " + t("Stift"))
        self.label_tool.setMinimumWidth(110)
        self.label_tool.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Stichtyp-Pill mit Accent-Secondary-Tint
        self.label_stitch_type = QLabel("✕ " + t("Voll"))
        self.label_stitch_type.setToolTip(
            t("Aktiver Stichtyp. Wechseln über das Stich-Menü oder Alt+1..7.")
        )
        self.label_stitch_type.setMinimumWidth(90)
        self.label_stitch_type.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Position: feste Breite gegen Zuckeln bei wechselnder Stellenzahl
        self.label_position = QLabel("X: 0  Y: 0")
        self.label_position.setMinimumWidth(120)
        self.label_position.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Farbe-unter-Maus: bereits min-width gesetzt
        self.label_color_info = QLabel(t("— leer —"))
        self.label_color_info.setMinimumWidth(200)
        self.label_color_info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label_layer = QLabel(t("Ebene:") + " -")
        self.label_layer.setMinimumWidth(140)
        self.label_layer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label_size = QLabel("50 × 50")
        self.label_size.setMinimumWidth(80)
        self.label_size.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label_stitches = QLabel("0 " + t("Stiche"))
        self.label_stitches.setMinimumWidth(100)
        self.label_stitches.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label_undo = QLabel(t("Undo:") + " 0")
        self.label_undo.setMinimumWidth(80)
        self.label_undo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Stylesheet-Klassen via dynamic properties — siehe _apply_statusbar_styles
        self.label_tool.setProperty("pill", "primary")
        self.label_stitch_type.setProperty("pill", "secondary")
        self.label_color_info.setProperty("pill", "muted")
        self.label_position.setProperty("pill", "info")
        self.label_layer.setProperty("pill", "purple")
        self.label_size.setProperty("pill", "muted")
        self.label_stitches.setProperty("pill", "primary")
        self.label_undo.setProperty("pill", "muted")
        self._apply_statusbar_styles()

        # Zoom-Slider
        self.zoom_slider = ZoomSlider()
        self.zoom_slider.zoom_changed.connect(self._on_zoom_slider_changed)
        self.zoom_slider.zoom_fit_requested.connect(self._on_zoom_fit)
        self.zoom_slider.zoom_100_requested.connect(self._on_zoom_100)

        # Sticken-Modus-Indikator — links in der Statusbar, sehr sichtbar wenn aktiv
        self.label_stitch_mode = QLabel("")
        self.label_stitch_mode.setVisible(False)
        self.status_bar.addWidget(self.label_stitch_mode)

        for label in [
            self.label_tool,
            self.label_stitch_type,
            self.label_position,
            self.label_color_info,
            self.label_layer,
            self.label_size,
            self.label_stitches,
            self.label_undo,
        ]:
            self.status_bar.addPermanentWidget(label)

        self.status_bar.addPermanentWidget(self.zoom_slider)

        self.status_bar.showMessage(t("Bereit"))

    def _update_stitch_mode_indicator(self, on: bool) -> None:
        """Zeigt/versteckt den prominenten Sticken-Modus-Indikator in der Statusbar."""
        from ..core.i18n import t
        from .styles import THEME

        if on:
            self.label_stitch_mode.setText("✓ " + t("STICKEN-MODUS AKTIV"))
            self.label_stitch_mode.setStyleSheet(
                f"QLabel {{ "
                f"background: {THEME.accent_primary}; "
                f"color: {THEME.bg_dark}; "
                f"padding: 2px 12px; "
                f"border-radius: 9px; "
                f"font-size: 11px; "
                f"font-weight: 700; "
                f"letter-spacing: 1px; "
                f"}}"
            )
            self.label_stitch_mode.setVisible(True)
        else:
            self.label_stitch_mode.setVisible(False)

    def _apply_statusbar_styles(self) -> None:
        """Wendet die Pill-Styles auf die Statusleisten-Labels an.

        Wird auch nach Theme-Wechseln aufgerufen.
        """
        from .styles import THEME

        # Helper fuer Pill-Style mit Tint
        def pill(bg_tint: str, fg: str) -> str:
            return (
                f"QLabel {{ "
                f"background: {bg_tint}; "
                f"color: {fg}; "
                f"padding: 2px 10px; "
                f"border-radius: 9px; "
                f"font-size: 11px; "
                f"font-weight: 600; "
                f"}}"
            )

        # Tints: leicht transparent-ueber-bg, damit die Pill nicht zu kraeftig wirkt
        primary_bg = QColor(THEME.accent_primary)
        primary_bg.setAlpha(50)
        secondary_bg = QColor(THEME.accent_secondary)
        secondary_bg.setAlpha(50)
        info_bg = QColor(THEME.info)
        info_bg.setAlpha(50)
        purple_bg = QColor(THEME.accent_purple)
        purple_bg.setAlpha(50)

        self.label_tool.setStyleSheet(
            pill(
                f"rgba({primary_bg.red()}, {primary_bg.green()}, {primary_bg.blue()}, {primary_bg.alpha()})",
                THEME.accent_primary,
            )
        )
        self.label_stitch_type.setStyleSheet(
            pill(
                f"rgba({secondary_bg.red()}, {secondary_bg.green()}, {secondary_bg.blue()}, {secondary_bg.alpha()})",
                THEME.accent_secondary,
            )
        )
        self.label_position.setStyleSheet(
            pill(
                f"rgba({info_bg.red()}, {info_bg.green()}, {info_bg.blue()}, {info_bg.alpha()})",
                THEME.info,
            )
        )
        self.label_layer.setStyleSheet(
            pill(
                f"rgba({purple_bg.red()}, {purple_bg.green()}, {purple_bg.blue()}, {purple_bg.alpha()})",
                THEME.accent_purple,
            )
        )
        muted_style = pill(THEME.bg_light, THEME.text_secondary)
        self.label_color_info.setStyleSheet(muted_style)
        self.label_size.setStyleSheet(muted_style)
        self.label_stitches.setStyleSheet(
            pill(
                f"rgba({primary_bg.red()}, {primary_bg.green()}, {primary_bg.blue()}, {primary_bg.alpha()})",
                THEME.accent_primary,
            )
        )
        self.label_undo.setStyleSheet(muted_style)

    # =========================================================================
    # Status-Methoden
    # =========================================================================

    def _update_title(self) -> None:
        """Aktualisiert den Fenstertitel. Zeigt aktiven Modus prominent an."""
        from ..core.i18n import t

        mode = getattr(self.current_pattern, "mode", "stitch")
        mode_label = t("Diamond Painting") if mode == "diamond" else t("Kreuzstich")
        mode_icon = "💎" if mode == "diamond" else "🧵"
        title = f"{APP_NAME} {mode_icon} {mode_label}"
        if self.current_file:
            name = self.current_file.name
        elif self.current_pattern.name != "Neues Muster":
            name = self.current_pattern.name
        else:
            name = t("Unbenannt")
        if self._unsaved_changes:
            name = f"*{name}"
        self.setWindowTitle(f"{name} - {title}")

    def _update_status(self) -> None:
        """Aktualisiert die Statusleiste. Im DP-Modus 'Drills' statt 'Stiche'."""
        from ..core.i18n import t

        stats = self.current_pattern.get_statistics()
        self.label_size.setText(f"{stats['width']} × {stats['height']}")
        unit = (
            t("Drills")
            if getattr(self.current_pattern, "mode", "stitch") == "diamond"
            else t("Stiche")
        )
        self.label_stitches.setText(f"{stats['total_stitches']} {unit}")
        layer = self.current_pattern.active_layer
        if layer:
            self.label_layer.setText(f"{t('Ebene:')} {t(layer.name)}")

    def _update_undo_actions(self) -> None:
        """Aktualisiert Undo/Redo-Actions."""
        from ..core.i18n import t

        can_undo = self.undo_manager.can_undo
        can_redo = self.undo_manager.can_redo
        self.action_undo.setEnabled(can_undo)
        self.action_redo.setEnabled(can_redo)
        undo_label = t("&Rückgängig")
        redo_label = t("&Wiederholen")
        self.action_undo.setText(
            f"{undo_label}: {self.undo_manager.undo_description}" if can_undo else undo_label
        )
        self.action_redo.setText(
            f"{redo_label}: {self.undo_manager.redo_description}" if can_redo else redo_label
        )
        self.label_undo.setText(f"{t('Undo:')} {self.undo_manager.undo_count}")

    def _mark_unsaved(self) -> None:
        """Markiert das Dokument als ungespeichert."""
        if not self._unsaved_changes:
            self._unsaved_changes = True
            self._update_title()

    def _mark_saved(self) -> None:
        """Markiert das Dokument als gespeichert."""
        self._unsaved_changes = False
        self._update_title()

    # =========================================================================
    # Panel-Koordination
    # =========================================================================

    def _notify_panels(self, scope: str | tuple[str, ...] = "full") -> None:
        """Benachrichtigt Panels über Änderungen.

        Args:
            scope: Einzelner Scope-String oder Tupel mehrerer Scopes.
                   Verwende NotifyScope-Konstanten.

        Scopes:
          "full"     - Neues Pattern geladen (alle Panels + Status)
          "stitch"   - Stich-Änderung (info, color_bar, status)
          "visual"   - Visuelles Refresh (canvas, minimap, tile_preview)
          "progress" - Fortschritt (progress_panel, info, status, undo)
          "palette"  - Palette geändert (color_bar, info, palette, minimap, tile)
        """
        if isinstance(scope, tuple):
            for s in scope:
                self._notify_panels(s)
            return

        p = self.current_pattern
        if scope == "full":
            # Bulk-Update: Repaint waehrend des kompletten Pattern-Rebuilds
            # aussetzen. Beim Laden eines Patterns ueber "Zuletzt geoeffnet"
            # poppte sonst gelegentlich ein leeres Top-Level-Phantomfenster
            # auf — Qt rendert frisch konstruierte Widgets (ColorListItems,
            # Swatches, Tile-Previews) kurz unparented vor dem Layout-Einbau.
            # setUpdatesEnabled(False) auf das MainWindow unterdrueckt all
            # diese Zwischen-Repaints und triggert einen einzelnen sauberen
            # Paint am Ende.
            self.setUpdatesEnabled(False)
            try:
                self.canvas_container.set_pattern(p)
                self.color_bar.set_pattern(p)
                self.layer_panel.set_layer_stack(p.layer_stack)
                # Pattern-Modus auf UI uebertragen — VOR update_info, damit das
                # Info-Panel direkt die richtigen Labels rendert.
                self._apply_pattern_mode(
                    p is not None and getattr(p, "mode", "stitch") == "diamond",
                    palette_auto_switch=False,
                )
                self.info_panel.update_info(p)
                self.palette_panel.set_pattern(p)
                self.minimap_panel.set_pattern(p)
                self.tile_preview_panel.set_pattern(p)
                self.progress_panel.update_progress(p)
                self._update_status()
                self._update_undo_actions()
            finally:
                self.setUpdatesEnabled(True)
        elif scope == "stitch":
            self._update_status()
            self.info_panel.update_info(p)
            self.color_bar.update_swatches()
        elif scope == "visual":
            self.canvas.update()
            self.minimap_panel.refresh()
            self.tile_preview_panel.refresh()
        elif scope == "progress":
            self.progress_panel.update_progress(p)
            self.info_panel.update_info(p)
            self._update_status()
            self._update_undo_actions()
        elif scope == "palette":
            self.canvas.update()
            self.color_bar.refresh()
            self.info_panel.update_info(p)
            self.minimap_panel.refresh()
            self.tile_preview_panel.refresh()
            self.palette_panel.refresh_used_colors()

    def _exec_edit_dialog(
        self,
        dialog,
        scope: str | tuple[str, ...],
        message: str,
        timeout: int = 3000,
    ) -> bool:
        """Führt einen Edit-Dialog aus und aktualisiert bei Erfolg UI.

        Für Dialoge die das bestehende Pattern modifizieren (Farben, Palette, etc.).

        Args:
            dialog: Der auszuführende QDialog.
            scope: NotifyScope für Panel-Updates.
            message: Statusbar-Nachricht bei Erfolg.
            timeout: Anzeigedauer der Statusbar-Nachricht in ms.

        Returns:
            True wenn Dialog akzeptiert wurde.
        """
        if dialog.exec():
            self._notify_panels(scope)
            self._mark_unsaved()
            self.status_bar.showMessage(message, timeout)
            return True
        return False

    def _exec_import_dialog(self, dialog, message: str, timeout: int = 5000) -> bool:
        """Führt einen Import-Dialog aus und setzt bei Erfolg das neue Pattern.

        Für Dialoge die ein neues Pattern erzeugen (Bild-Import, XSD/PAT-Import).
        Erwartet `dialog.get_pattern()` als Methode auf dem Dialog.

        Args:
            dialog: Der auszuführende QDialog mit get_pattern()-Methode.
            message: Statusbar-Nachricht bei Erfolg.
            timeout: Anzeigedauer der Statusbar-Nachricht in ms.

        Returns:
            True wenn Dialog akzeptiert und Pattern gesetzt wurde.
        """
        if dialog.exec():
            pattern = dialog.get_pattern()
            if pattern:
                self.current_file = None
                self.set_pattern(pattern)
                self._mark_unsaved()
                self.status_bar.showMessage(message, timeout)
                return True
        return False

    def set_pattern(self, pattern: Pattern) -> None:
        """Setzt ein neues Pattern und aktualisiert alle Panels."""
        self.current_pattern = pattern
        self.undo_manager.set_pattern(pattern)
        self._notify_panels(NotifyScope.FULL)
        self._update_title()
        # Pattern wurde explizit gesetzt — Welcome-Screen verschwindet,
        # und _perform_start_action darf ihn nicht spaeter wieder zeigen
        # (relevant beim Start mit Demo-Pattern oder via Recovery).
        self._pattern_explicitly_set = True
        if hasattr(self, "canvas_container"):
            self.canvas_container.show_welcome(False)
        QTimer.singleShot(100, self.canvas.zoom_fit)
        QTimer.singleShot(200, self._update_minimap_viewport)

    # === Welcome-Widget Handler ===

    def _on_welcome_new(self) -> None:
        """Welcome -> Neues Muster."""
        self.canvas_container.show_welcome(False)
        self._on_new()

    def _on_welcome_open(self) -> None:
        """Welcome -> Datei oeffnen."""
        self.canvas_container.show_welcome(False)
        self._on_open()

    def _on_welcome_import(self) -> None:
        """Welcome -> Bild importieren."""
        self.canvas_container.show_welcome(False)
        self._on_import_image()

    def _on_welcome_open_recent(self, path: str) -> None:
        """Welcome -> Recent-Datei oeffnen."""
        self.canvas_container.show_welcome(False)
        self._open_recent_file(path)

    def _on_open_demo(self) -> None:
        """Laedt das mitgelieferte Demo-Muster aus
        `resources/examples/demo_kreuzstich.pxs` in eine User-schreibbare
        Kopie. So kann der User das Demo speichern/aendern, ohne die
        Bundled-Datei zu beruehren.
        """
        from ..core import load_pattern

        bundled = Path(__file__).parent.parent / "resources" / "examples" / "demo_kreuzstich.pxs"
        if not bundled.exists():
            QMessageBox.warning(
                self,
                "Demo nicht verfuegbar",
                f"Demo-Datei nicht gefunden:\n{bundled}",
            )
            return

        try:
            pattern = load_pattern(str(bundled))
        except (OSError, ValueError) as e:
            QMessageBox.warning(
                self,
                "Demo konnte nicht geladen werden",
                str(e),
            )
            return

        self.canvas_container.show_welcome(False)
        self.set_pattern(pattern)
        # Demo soll als "neue Datei" gelten — User kann via "Speichern unter"
        # eine eigene Kopie ablegen. current_file None lassen.
        self.current_file = None
        self._unsaved_changes = False
        self._update_title()
        self.status_bar.showMessage(
            "Demo-Muster geladen. Speichern unter… legt eine eigene Kopie an. "
            "Probier den Sticken-Modus (Strg+M) oder Strg+H!",
            7000,
        )

    def add_color_to_pattern(self, thread: Thread) -> int:
        """Fügt eine Farbe zum Pattern hinzu, falls nicht vorhanden.

        Wenn der Thread aus einer Bead-Palette stammt, wird der Eintrag als
        Bead markiert — Stiche dieser Farbe werden dann automatisch als
        BEAD-Stitch-Type platziert.
        """
        for i, entry in enumerate(self.current_pattern.color_entries):
            if (
                entry.thread.catalog_number == thread.catalog_number
                and entry.thread.manufacturer == thread.manufacturer
            ):
                return i
        # Pruefen ob Thread aus einer Bead- oder Diamond-Painting-Palette stammt
        from ..core.palette import get_palette_manager

        pm = get_palette_manager()
        is_bead = False
        is_diamond = False
        if thread.manufacturer:
            palette = pm.get_palette(thread.manufacturer)
            if palette is not None:
                is_bead = palette.is_beads
                is_diamond = palette.is_diamond
        index = self.current_pattern.add_color(thread, is_bead=is_bead, is_diamond=is_diamond)
        self.color_bar.set_pattern(self.current_pattern)
        self.info_panel.update_info(self.current_pattern)
        return index

    # Undo/Redo, Panel/Color, Tool, Layer, Recent Files, Templates,
    # Autosave, Shortcuts, About, Settings Handler:
    # → Siehe Handler-Mixins in ui/handlers/

    # =========================================================================
    # Events
    # =========================================================================

    def keyPressEvent(self, event) -> None:
        """Tastendruck-Event."""
        if event.key() == Qt.Key.Key_Question:
            self._on_show_shortcuts()
        else:
            super().keyPressEvent(event)

    def dragEnterEvent(self, event) -> None:
        """Akzeptiert Drag&Drop von .pxs-, Bild- und externen Pattern-Dateien."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                lower = url.toLocalFile().lower()
                if lower.endswith(
                    (
                        ".pxs",
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".gif",
                        ".bmp",
                        ".oxs",
                        ".xsd",
                        ".pat",
                    )
                ):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event) -> None:
        """Öffnet eine per Drag&Drop abgelegte Datei."""
        for url in event.mimeData().urls():
            filepath = url.toLocalFile()
            lower = filepath.lower()
            if lower.endswith(".pxs"):
                if not self._check_save_changes():
                    return
                self._load_pattern_file(filepath)
                return
            elif lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
                self._on_import_image(filepath)
                return
            elif lower.endswith((".oxs", ".xsd", ".pat")):
                if not self._check_save_changes():
                    return
                self._load_external_pattern_file(filepath)
                return

    def closeEvent(self, event) -> None:
        """Fenster-Schließen-Event."""
        # Laufende Stick-Session vor dem Save-Check stoppen, damit die
        # gemessene Zeit noch in der zu speichernden Datei landet.
        from ..core import session_timer

        if self.current_pattern is not None and session_timer.is_session_active(
            self.current_pattern
        ):
            elapsed = session_timer.stop_session(self.current_pattern)
            if elapsed > 0:
                self._mark_unsaved()

        if self._check_save_changes():
            # Fenstergeometrie und Layout speichern
            self._settings.setValue("window/geometry", self.saveGeometry())
            self._settings.setValue("window/state", self.saveState())
            event.accept()
        else:
            event.ignore()

    # =========================================================================
    # Start-Aktion
    # =========================================================================

    def _perform_start_action(self) -> None:
        """Führt die konfigurierte Start-Aktion aus."""
        # Zuerst auf Autosave-Recovery prüfen — falls Recovery passiert ist,
        # wurde set_pattern() bereits aufgerufen (Welcome dadurch ausgeblendet).
        self._check_autosave_recovery()

        start_action = self._settings.value("start_action", 0, type=int)

        # Helper: hat etwas im Pre-Start (Recovery, CLI, Demo) bereits ein
        # Pattern geladen? set_pattern() setzt _pattern_explicitly_set.
        def _already_loaded() -> bool:
            return (
                self.current_file is not None
                or self._unsaved_changes
                or getattr(self, "_pattern_explicitly_set", False)
            )

        if start_action == 0:
            # Default: Welcome-Screen zeigen
            if not _already_loaded():
                self.canvas_container.show_welcome(True, recent_files=self._recent_files)
                self.status_bar.showMessage("Willkommen bei PySticky", 3000)
            else:
                self.status_bar.showMessage("Bereit", 3000)
        elif start_action == 1:
            # Neues Projekt Dialog öffnen
            self._unsaved_changes = False
            self._on_new()
        elif start_action == 2:
            # Letzte Datei öffnen — Fallback: Welcome wenn keine Recent
            opened = False
            if self._recent_files:
                last_file = self._recent_files[0]
                if Path(last_file).exists():
                    self._unsaved_changes = False
                    self._open_recent_file(last_file)
                    opened = True
                else:
                    self.status_bar.showMessage("Letzte Datei nicht gefunden", 3000)
            if not opened and not _already_loaded():
                self.canvas_container.show_welcome(True, recent_files=self._recent_files)
        elif start_action == 3:
            # Nichts tun — aber Welcome-Screen zeigen wenn nichts geladen wurde
            # (sonst hat der User ein leeres Fenster ohne Hinweis).
            if not _already_loaded():
                self.canvas_container.show_welcome(True, recent_files=self._recent_files)
