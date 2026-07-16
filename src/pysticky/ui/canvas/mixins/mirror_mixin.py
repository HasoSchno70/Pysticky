"""
Spiegelmodus-Mixin für Canvas.

Enthält Methoden für Spiegelberechnungen und Auswahl-Spiegelung.
"""

from typing import TYPE_CHECKING

from ..enums import MirrorMode

if TYPE_CHECKING:
    from ..canvas import CrossStitchCanvas


class MirrorMixin:
    """Mixin für Spiegelmodus-Funktionalität."""

    def get_mirrored_positions(self: "CrossStitchCanvas", x: int, y: int) -> list[tuple[int, int]]:
        """Gibt alle gespiegelten Positionen basierend auf dem Spiegelmodus zurück."""
        if not self._pattern:
            return [(x, y)]

        positions = {(x, y)}

        center_x = self._pattern.width / 2
        center_y = self._pattern.height / 2

        # Relative Position zum Zentrum
        dx = x - center_x + 0.5
        dy = y - center_y + 0.5

        mode = self._mirror_mode

        # Horizontale Spiegelung (vertikal zur Achse)
        if mode in (MirrorMode.HORIZONTAL, MirrorMode.QUAD, MirrorMode.OCTAL):
            mirror_x = int(center_x - dx - 0.5)
            if 0 <= mirror_x < self._pattern.width:
                positions.add((mirror_x, y))

        # Vertikale Spiegelung (horizontal zur Achse)
        if mode in (MirrorMode.VERTICAL, MirrorMode.QUAD, MirrorMode.OCTAL):
            mirror_y = int(center_y - dy - 0.5)
            if 0 <= mirror_y < self._pattern.height:
                positions.add((x, mirror_y))

        # 4-fach: Diagonal gegenüber
        if mode in (MirrorMode.QUAD, MirrorMode.OCTAL):
            mirror_x = int(center_x - dx - 0.5)
            mirror_y = int(center_y - dy - 0.5)
            if 0 <= mirror_x < self._pattern.width and 0 <= mirror_y < self._pattern.height:
                positions.add((mirror_x, mirror_y))

        # 8-fach: Diagonale Spiegelungen
        if mode == MirrorMode.OCTAL:
            # Spiegelung an der Diagonale
            diag_x = int(center_x + dy - 0.5)
            diag_y = int(center_y + dx - 0.5)
            if 0 <= diag_x < self._pattern.width and 0 <= diag_y < self._pattern.height:
                positions.add((diag_x, diag_y))

            # Spiegelung an der Anti-Diagonale
            anti_x = int(center_x - dy - 0.5)
            anti_y = int(center_y - dx - 0.5)
            if 0 <= anti_x < self._pattern.width and 0 <= anti_y < self._pattern.height:
                positions.add((anti_x, anti_y))

            # Kombinationen
            combo1_x = int(center_x - dy - 0.5)
            combo1_y = int(center_y + dx - 0.5)
            if 0 <= combo1_x < self._pattern.width and 0 <= combo1_y < self._pattern.height:
                positions.add((combo1_x, combo1_y))

            combo2_x = int(center_x + dy - 0.5)
            combo2_y = int(center_y - dx - 0.5)
            if 0 <= combo2_x < self._pattern.width and 0 <= combo2_y < self._pattern.height:
                positions.add((combo2_x, combo2_y))

        # Legacy-Kompatibilität für alte mirror_horizontal/vertical Properties
        if mode == MirrorMode.NONE:
            if self._mirror_horizontal:
                mirror_x = int(2 * center_x - x - 1)
                if 0 <= mirror_x < self._pattern.width:
                    positions.add((mirror_x, y))

            if self._mirror_vertical:
                mirror_y = int(2 * center_y - y - 1)
                if 0 <= mirror_y < self._pattern.height:
                    positions.add((x, mirror_y))

            if self._mirror_horizontal and self._mirror_vertical:
                mirror_x = int(2 * center_x - x - 1)
                mirror_y = int(2 * center_y - y - 1)
                if 0 <= mirror_x < self._pattern.width and 0 <= mirror_y < self._pattern.height:
                    positions.add((mirror_x, mirror_y))

        return list(positions)

    def _has_mirror_active(self: "CrossStitchCanvas") -> bool:
        """Prüft ob irgendein Spiegelmodus aktiv ist."""
        return (
            self._mirror_mode != MirrorMode.NONE or self._mirror_horizontal or self._mirror_vertical
        )

    def mirror_selection_horizontal(self: "CrossStitchCanvas") -> bool:
        """Spiegelt die Auswahl horizontal."""
        if not self._pattern or not self._selection:
            return False

        layer = self._pattern.active_layer
        if not layer:
            return False

        x1, y1 = self._selection.left(), self._selection.top()
        x2, y2 = self._selection.right(), self._selection.bottom()

        data = []
        for y in range(y1, y2 + 1):
            row = [layer.get_stitch(x, y) for x in range(x1, x2 + 1)]
            data.append(row)

        for y_idx, row in enumerate(data):
            row.reverse()
            for x_idx, color_idx in enumerate(row):
                x, y = x1 + x_idx, y1 + y_idx
                if color_idx is not None:
                    layer.set_stitch(x, y, color_idx)
                else:
                    layer.remove_stitch(x, y)

        return True

    def mirror_selection_vertical(self: "CrossStitchCanvas") -> bool:
        """Spiegelt die Auswahl vertikal."""
        if not self._pattern or not self._selection:
            return False

        layer = self._pattern.active_layer
        if not layer:
            return False

        x1, y1 = self._selection.left(), self._selection.top()
        x2, y2 = self._selection.right(), self._selection.bottom()

        data = []
        for y in range(y1, y2 + 1):
            row = [layer.get_stitch(x, y) for x in range(x1, x2 + 1)]
            data.append(row)

        data.reverse()
        for y_idx, row in enumerate(data):
            for x_idx, color_idx in enumerate(row):
                x, y = x1 + x_idx, y1 + y_idx
                if color_idx is not None:
                    layer.set_stitch(x, y, color_idx)
                else:
                    layer.remove_stitch(x, y)

        return True
