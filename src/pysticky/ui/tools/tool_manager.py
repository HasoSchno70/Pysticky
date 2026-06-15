"""
Werkzeug-Manager - Verwaltet alle verfügbaren Werkzeuge.
"""

from typing import TYPE_CHECKING, Type, TypeVar

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QPainter

from .backstitch_tool import BackstitchTool
from .base_tool import BaseTool, ToolContext
from .ellipse_tool import EllipseTool
from .eraser_tool import EraserTool
from .fill_tool import FillTool
from .gradient_tool import GradientTool
from .lasso_select_tool import LassoSelectTool
from .line_tool import LineTool
from .move_tool import MoveTool
from .pencil_tool import PencilTool
from .pipette_tool import PipetteTool
from .polygon_tool import PolygonTool
from .progress_tool import ProgressTool
from .rect_tool import RectTool
from .select_tool import SelectTool
from .text_tool import TextTool
from .tool_enum import Tool

if TYPE_CHECKING:
    pass


T = TypeVar("T", bound=BaseTool)


class ToolManager:
    """
    Verwaltet alle Zeichenwerkzeuge und delegiert Events.
    """

    def __init__(self) -> None:
        self._tools: dict[Tool, BaseTool] = {}
        self._current_tool: Tool = Tool.PENCIL
        self._setup_tools()

    def _setup_tools(self) -> None:
        """Initialisiert alle verfügbaren Werkzeuge."""
        self._tools = {
            # Zeichenwerkzeuge
            Tool.PENCIL: PencilTool(),
            Tool.ERASER: EraserTool(),
            Tool.FILL: FillTool(),
            Tool.PIPETTE: PipetteTool(),
            # Linien & Formen
            Tool.LINE: LineTool(),
            Tool.RECT: RectTool(filled=False),
            Tool.RECT_FILLED: RectTool(filled=True),
            Tool.ELLIPSE: EllipseTool(filled=False),
            Tool.ELLIPSE_FILLED: EllipseTool(filled=True),
            Tool.POLYGON: PolygonTool(filled=False),
            Tool.POLYGON_FILLED: PolygonTool(filled=True),
            # Spezialwerkzeuge
            Tool.TEXT: TextTool(),
            Tool.BACKSTITCH: BackstitchTool(),
            Tool.GRADIENT: GradientTool(),
            # Auswahl
            Tool.SELECT: SelectTool(),
            Tool.SELECT_LASSO: LassoSelectTool(),
            # Navigation (no-op fuer Klicks, Pan via Mittelmaus)
            Tool.MOVE: MoveTool(),
            # Fortschritt
            Tool.PROGRESS: ProgressTool(),
        }

    @property
    def current_tool(self) -> Tool:
        """Aktuelles Werkzeug."""
        return self._current_tool

    @current_tool.setter
    def current_tool(self, tool: Tool) -> None:
        """Setzt das aktuelle Werkzeug."""
        if tool == self._current_tool:
            return

        # Altes Werkzeug deaktivieren
        if self._current_tool in self._tools:
            self._tools[self._current_tool].deactivate()

        self._current_tool = tool

        # Neues Werkzeug aktivieren
        if tool in self._tools:
            self._tools[tool].activate()

    def get_tool(self, tool: Tool) -> BaseTool | None:
        """Gibt ein Werkzeug zurück."""
        return self._tools.get(tool)

    def get_tool_as(self, tool: Tool, tool_class: Type[T]) -> T | None:
        """
        Gibt ein Werkzeug mit Typ-Cast zurück.

        Beispiel:
            text_tool = manager.get_tool_as(Tool.TEXT, TextTool)
            if text_tool:
                text_tool.set_text("Hello")
        """
        tool_instance = self._tools.get(tool)
        if isinstance(tool_instance, tool_class):
            return tool_instance
        return None

    def get_active_tool(self) -> BaseTool | None:
        """Gibt das aktive Werkzeug zurück."""
        return self._tools.get(self._current_tool)

    def get_cursor(self) -> Qt.CursorShape:
        """Gibt den Cursor für das aktuelle Werkzeug zurück."""
        tool = self.get_active_tool()
        return tool.get_cursor() if tool else Qt.CursorShape.ArrowCursor

    # === Event-Delegation ===

    def on_mouse_press(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        """Delegiert Mouse-Press an aktives Werkzeug."""
        tool = self.get_active_tool()
        return tool.on_mouse_press(ctx, event) if tool else []

    def on_mouse_move(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        """Delegiert Mouse-Move an aktives Werkzeug."""
        tool = self.get_active_tool()
        return tool.on_mouse_move(ctx, event) if tool else []

    def on_mouse_release(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        """Delegiert Mouse-Release an aktives Werkzeug."""
        tool = self.get_active_tool()
        return tool.on_mouse_release(ctx, event) if tool else []

    def on_key_press(self, ctx: ToolContext, event: QKeyEvent) -> bool:
        """Delegiert Key-Press an aktives Werkzeug."""
        tool = self.get_active_tool()
        return tool.on_key_press(ctx, event) if tool else False

    def draw_preview(self, ctx: ToolContext, painter: QPainter) -> None:
        """Zeichnet die Vorschau des aktiven Werkzeugs."""
        tool = self.get_active_tool()
        if tool:
            # SelectTool und LassoSelectTool zeigen Auswahl immer an
            if isinstance(tool, (SelectTool, LassoSelectTool)) or tool.is_active:
                tool.draw_preview(ctx, painter)

    def is_tool_active(self) -> bool:
        """Prüft ob ein Werkzeug gerade aktiv ist (z.B. beim Zeichnen)."""
        tool = self.get_active_tool()
        return tool.is_active if tool else False

    # === Convenience-Getter ===

    def get_text_tool(self) -> TextTool | None:
        """Gibt das Text-Werkzeug zurück."""
        return self.get_tool_as(Tool.TEXT, TextTool)

    def get_select_tool(self) -> SelectTool | None:
        """Gibt das Rechteck-Auswahl-Werkzeug zurück."""
        return self.get_tool_as(Tool.SELECT, SelectTool)

    def get_lasso_tool(self) -> LassoSelectTool | None:
        """Gibt das Lasso-Auswahl-Werkzeug zurück."""
        return self.get_tool_as(Tool.SELECT_LASSO, LassoSelectTool)

    def get_active_select_tool(self) -> SelectTool | LassoSelectTool | None:
        """Gibt das aktive Auswahl-Werkzeug zurück (Rechteck oder Lasso)."""
        if self._current_tool == Tool.SELECT_LASSO:
            return self.get_lasso_tool()
        elif self._current_tool == Tool.SELECT:
            return self.get_select_tool()
        # Fallback: Prüfe ob eines der Tools eine aktive Auswahl hat
        lasso = self.get_lasso_tool()
        if lasso and lasso.selected_pixels:
            return lasso
        return self.get_select_tool()

    def get_backstitch_tool(self) -> BackstitchTool | None:
        """Gibt das Rückstich-Werkzeug zurück."""
        return self.get_tool_as(Tool.BACKSTITCH, BackstitchTool)

    def get_gradient_tool(self) -> GradientTool | None:
        """Gibt das Farbverlauf-Werkzeug zurück."""
        return self.get_tool_as(Tool.GRADIENT, GradientTool)

    def get_progress_tool(self) -> ProgressTool | None:
        """Gibt das Fortschritts-Werkzeug zurück."""
        return self.get_tool_as(Tool.PROGRESS, ProgressTool)

    def get_pipette_color(self) -> int | None:
        """Gibt die von der Pipette aufgenommene Farbe zurück."""
        pipette = self.get_tool_as(Tool.PIPETTE, PipetteTool)
        return pipette.picked_color_index if pipette else None
