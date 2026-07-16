"""
Werkzeug-Definitionen (Tool Enum).

Zentralisiert alle Tool-Namen und -Beschreibungen an einer Stelle.
"""

from enum import Enum, auto


class Tool(Enum):
    """Verfügbare Werkzeuge mit deutschen Anzeigenamen."""

    # Zeichenwerkzeuge
    PENCIL = auto()
    ERASER = auto()
    FILL = auto()
    PIPETTE = auto()

    # Formwerkzeuge (mit Umriss/Gefüllt-Toggle)
    LINE = auto()
    RECT = auto()
    RECT_FILLED = auto()
    ELLIPSE = auto()
    ELLIPSE_FILLED = auto()
    POLYGON = auto()
    POLYGON_FILLED = auto()

    # Text
    TEXT = auto()

    # Rückstich
    BACKSTITCH = auto()

    # Spezialwerkzeuge
    GRADIENT = auto()

    # Auswahl & Navigation
    SELECT = auto()
    SELECT_LASSO = auto()
    MOVE = auto()

    # Fortschritt
    PROGRESS = auto()

    # Transformationen (Aktionen, keine Werkzeuge)
    MIRROR_H = auto()
    MIRROR_V = auto()

    @property
    def display_name(self) -> str:
        """Gibt den deutschen Anzeigenamen für die Statusleiste zurück."""
        return _TOOL_DISPLAY_NAMES.get(self, "Unbekannt")

    @property
    def batch_description(self) -> str:
        """Gibt die Beschreibung für Undo-Batches zurück."""
        return _TOOL_BATCH_DESCRIPTIONS.get(self, "Zeichnen")

    @property
    def shortcut(self) -> str:
        """Gibt das Tastenkürzel für das Werkzeug zurück."""
        return _TOOL_SHORTCUTS.get(self, "")


# Anzeigenamen für die Statusleiste (UI-freundlich)
_TOOL_DISPLAY_NAMES: dict["Tool", str] = {
    Tool.PENCIL: "Stift",
    Tool.ERASER: "Radierer",
    Tool.FILL: "Füllen",
    Tool.PIPETTE: "Pipette",
    Tool.LINE: "Linie",
    Tool.RECT: "Rechteck (Umriss)",
    Tool.RECT_FILLED: "Rechteck (gefüllt)",
    Tool.ELLIPSE: "Ellipse (Umriss)",
    Tool.ELLIPSE_FILLED: "Ellipse (gefüllt)",
    Tool.POLYGON: "Polygon (Umriss)",
    Tool.POLYGON_FILLED: "Polygon (gefüllt)",
    Tool.TEXT: "Text",
    Tool.BACKSTITCH: "Rückstich",
    Tool.GRADIENT: "Farbverlauf",
    Tool.SELECT: "Auswahl (Rechteck)",
    Tool.SELECT_LASSO: "Auswahl (Lasso)",
    Tool.MOVE: "Verschieben",
    Tool.PROGRESS: "Fortschritt",
    Tool.MIRROR_H: "H-Spiegeln",
    Tool.MIRROR_V: "V-Spiegeln",
}

# Batch-Beschreibungen für Undo (Aktionsnamen)
_TOOL_BATCH_DESCRIPTIONS: dict["Tool", str] = {
    Tool.PENCIL: "Zeichnen",
    Tool.ERASER: "Löschen",
    Tool.FILL: "Füllen",
    Tool.PIPETTE: "Pipette",
    Tool.LINE: "Linie",
    Tool.RECT: "Rechteck",
    Tool.RECT_FILLED: "Rechteck (gefüllt)",
    Tool.ELLIPSE: "Ellipse",
    Tool.ELLIPSE_FILLED: "Ellipse (gefüllt)",
    Tool.POLYGON: "Polygon",
    Tool.POLYGON_FILLED: "Polygon (gefüllt)",
    Tool.TEXT: "Text",
    Tool.BACKSTITCH: "Rückstich",
    Tool.GRADIENT: "Farbverlauf",
    Tool.SELECT: "Auswahl",
    Tool.SELECT_LASSO: "Lasso-Auswahl",
    Tool.MOVE: "Verschieben",
    Tool.PROGRESS: "Fortschritt markieren",
}

# Tastenkürzel — Single Source of Truth.
# Diese Werte müssen mit den Shortcuts in widgets/tool_bar.py übereinstimmen,
# damit die Settings/Shortcuts-Tab die Realität zeigt.
_TOOL_SHORTCUTS: dict["Tool", str] = {
    Tool.PENCIL: "P",
    Tool.ERASER: "E",
    Tool.FILL: "F",
    Tool.PIPETTE: "I",
    Tool.LINE: "L",
    Tool.RECT: "R",
    Tool.RECT_FILLED: "Shift+R",
    Tool.ELLIPSE: "O",
    Tool.ELLIPSE_FILLED: "Shift+O",
    Tool.POLYGON: "G",
    Tool.POLYGON_FILLED: "Shift+G",
    Tool.TEXT: "T",
    Tool.BACKSTITCH: "B",
    Tool.GRADIENT: "D",
    Tool.SELECT: "S",
    Tool.SELECT_LASSO: "Shift+S",
    Tool.MOVE: "M",
    Tool.PROGRESS: "K",
}
