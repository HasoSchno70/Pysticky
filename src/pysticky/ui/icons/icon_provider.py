"""
Icon-Provider für PySticky.

Verwendet SVG-Icons oder Emoji-Fallbacks.
Unterstützt Theme-abhängige Farben.
"""

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon, QPainter, QPixmap

from ..styles import THEME


class IconProvider:
    """
    Zentraler Icon-Provider für die Anwendung.

    Rendert Icons als SVG oder Emoji-Fallback mit konsistenten Farben.
    """

    # Icon-Definitionen: name -> (emoji_fallback, svg_path oder None)
    ICONS = {
        # Datei
        "new": ("📄", "document-new"),
        "open": ("📂", "document-open"),
        "save": ("💾", "document-save"),
        "export": ("📤", "document-export"),
        "import": ("📥", "document-import"),
        # Bearbeiten
        "undo": ("↩", "edit-undo"),
        "redo": ("↪", "edit-redo"),
        "cut": ("✂", "edit-cut"),
        "copy": ("📋", "edit-copy"),
        "paste": ("📌", "edit-paste"),
        "delete": ("🗑", "edit-delete"),
        # Ansicht
        "zoom_in": ("🔍", "zoom-in"),
        "zoom_out": ("🔎", "zoom-out"),
        "zoom_fit": ("⬜", "zoom-fit-best"),
        "zoom_100": ("🔲", "zoom-original"),
        # Werkzeuge
        "pencil": ("✏", "draw-freehand"),
        "eraser": ("🧹", "draw-eraser"),
        "fill": ("🪣", "color-fill"),
        "pipette": ("💉", "color-picker"),
        "line": ("📏", "draw-line"),
        "rect": ("▭", "draw-rectangle"),
        "ellipse": ("⬭", "draw-ellipse"),
        "polygon": ("⬡", "draw-polygon"),
        "text": ("T", "draw-text"),
        "select": ("�default", "select-rectangular"),
        "move": ("✥", "transform-move"),
        "backstitch": ("╲", "draw-path"),
        "gradient": ("🌈", "color-gradient"),
        # Ebenen
        "layer_new": ("➕", "layer-new"),
        "layer_delete": ("➖", "layer-delete"),
        "layer_up": ("⬆", "layer-raise"),
        "layer_down": ("⬇", "layer-lower"),
        "layer_visible": ("👁", "layer-visible-on"),
        "layer_hidden": ("👁‍🗨", "layer-visible-off"),
        "layer_locked": ("🔒", "object-locked"),
        "layer_unlocked": ("🔓", "object-unlocked"),
        # Symmetrie
        "mirror_h": ("↔", "object-flip-horizontal"),
        "mirror_v": ("↕", "object-flip-vertical"),
        "center": ("✛", "format-justify-center"),
        # Sonstiges
        "settings": ("⚙", "preferences-system"),
        "help": ("❓", "help-about"),
        "info": ("ℹ", "dialog-information"),
        "warning": ("⚠", "dialog-warning"),
        "error": ("❌", "dialog-error"),
        "success": ("✓", "dialog-ok"),
        "snap": ("🧲", "snap-grid"),
        "grid": ("⊞", "view-grid"),
        "symbols": ("🔠", "font"),
    }

    _cache: dict[tuple[str, int, str, float], QIcon] = {}

    @classmethod
    def _current_device_pixel_ratio(cls) -> float:
        """Liest das devicePixelRatio des primären Bildschirms als statische Annäherung.

        Anders als der Chunk-Cache (`ui/canvas/performance.py`), der pro Frame neu
        rendert und daher live auf `canvas.devicePixelRatioF()` reagieren kann/muss,
        ist `IconProvider` ein statischer, klassenweiter Cache ohne Bezug zu einem
        konkreten Widget/Screen. Ein einmalig gelesener Bildschirm-DPR-Wert ist hier
        ein bewusster, dokumentierter Kompromiss (HiDPI-Audit Runde 40, Nachtrag zu
        Runde 39): er deckt den weit überwiegenden Fall (ein Monitor, eine Skalierung
        für die gesamte Sitzung) ab, ohne einen DPR-Parameter durch jeden einzelnen
        Aufrufer im ganzen Code hindurchzureichen. Ein Wechsel auf einen anders
        skalierten Monitor *während* der Laufzeit zieht bereits gecachte Icons nicht
        automatisch nach -- das ist für uniform-uncharfe Icons (nicht größen-
        eskalierend wie beim Canvas) als geringere Schwere akzeptiert.
        """
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return 1.0
        return screen.devicePixelRatio()

    @classmethod
    def get_icon(cls, name: str, size: int = 24, color: str | None = None) -> QIcon:
        """
        Gibt ein Icon zurück.

        Args:
            name: Icon-Name (siehe ICONS)
            size: Größe in Pixeln
            color: Hex-Farbe oder None für Theme-Farbe

        Returns:
            QIcon-Instanz
        """
        if color is None:
            color = THEME.text_primary

        dpr = cls._current_device_pixel_ratio()
        cache_key = (name, size, color, dpr)
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        icon_def = cls.ICONS.get(name)
        if not icon_def:
            # Fallback: Fragezeichen
            icon_def = ("?", None)

        emoji, svg_name = icon_def

        # Versuche zuerst SVG zu laden (wenn implementiert)
        # Aktuell: Emoji-Fallback
        pixmap = cls._render_emoji_icon(emoji, size, color, dpr)

        icon = QIcon(pixmap)
        cls._cache[cache_key] = icon
        return icon

    @classmethod
    def get_pixmap(cls, name: str, size: int = 24, color: str | None = None) -> QPixmap:
        """Gibt ein Pixmap zurück."""
        return cls.get_icon(name, size, color).pixmap(QSize(size, size))

    @classmethod
    def _render_emoji_icon(
        cls, emoji: str, size: int, color: str, device_pixel_ratio: float = 1.0
    ) -> QPixmap:
        """Rendert ein Emoji als Icon mit der angegebenen Farbe.

        Die Pixmap wird in physischen Pixeln angelegt (`size * device_pixel_ratio`)
        und per `setDevicePixelRatio()` markiert, damit sie auf einem HiDPI-Bildschirm
        scharf statt hochskaliert-unscharf erscheint -- dasselbe Muster wie
        `render_chunk_to_pixmap` (`ui/canvas/performance.py`) und `_get_fabric_pixmap`
        (`ui/canvas/canvas.py`). Alle Zeichenoperationen bleiben unverändert in
        logischen Koordinaten, da QPainter das Skalieren für ein Gerät mit gesetztem
        DPR selbst übernimmt.
        """
        pixmap = QPixmap(
            max(1, round(size * device_pixel_ratio)),
            max(1, round(size * device_pixel_ratio)),
        )
        pixmap.setDevicePixelRatio(device_pixel_ratio)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Font für Emoji
        font = QFont("Segoe UI Emoji", int(size * 0.65))
        painter.setFont(font)
        painter.setPen(QColor(color))

        # Zentriert zeichnen (logische Koordinaten -- siehe Docstring oben)
        rect = QRect(0, 0, size, size)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, emoji)

        painter.end()
        return pixmap

    @classmethod
    def clear_cache(cls) -> None:
        """Leert den Icon-Cache (z.B. bei Theme-Wechsel)."""
        cls._cache.clear()


# Bequeme Funktion
def get_icon(name: str, size: int = 24, color: str | None = None) -> QIcon:
    """Shortcut für IconProvider.get_icon()."""
    return IconProvider.get_icon(name, size, color)
