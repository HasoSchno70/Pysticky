"""
Spiegelmodus-Mixin für Canvas.

Enthält Methoden für Spiegelberechnungen und Auswahl-Spiegelung.
"""

from typing import TYPE_CHECKING

from ....core.stitch import FLIP_H_MAP, FLIP_V_MAP
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

        # 8-fach: Diagonale Spiegelungen.
        #
        # Diese vier Formeln sind eine reine x/y-Transposition um das
        # Zentrum -- geometrisch nur eine echte 45-Grad-Diagonal-Spiegelung
        # bei einem QUADRATISCHEN Muster (width == height). Bei einem
        # rechteckigen Muster (der Normalfall) hat die tatsaechliche Eck-zu-
        # Eck-Diagonale einen anderen Winkel als 45 Grad; die Transpositions-
        # Formel produzierte dort ausserhalb bounds liegende (und damit
        # stillschweigend verworfene) Positionen, oder in Zentrumsnaehe eine
        # IM Muster liegende, aber geometrisch bedeutungslose Position (kein
        # echter Spiegelpunkt von irgendwas). "8-fach" degradierte dadurch
        # unbemerkt zu einem Mix aus teilweise fehlendem und teilweise
        # falsch platziertem 4-fach. Eine echte Spiegelung an der
        # tatsaechlichen (nicht-45-Grad) Rechteck-Diagonale ist eine eigene,
        # nicht-triviale Geometrieaufgabe (Ziel-Zellen muessten auf dem
        # Ganzzahl-Gitter gerundet werden, mit Kollisionsrisiko) -- als
        # sichere Zwischenloesung faellt Oktal bei nicht-quadratischen
        # Mustern auf die bereits korrekte 4-fach-Spiegelung zurueck, statt
        # falsche/fehlende Daten zu erzeugen.
        if mode == MirrorMode.OCTAL and self._pattern.width == self._pattern.height:
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

    def get_mirrored_backstitch_lines(
        self: "CrossStitchCanvas", x1: int, y1: int, x2: int, y2: int
    ) -> list[tuple[int, int, int, int]]:
        """Gibt alle gespiegelten Varianten einer Rückstich-Linie zurück.

        Rückstich-Koordinaten sind in halben Stichen (siehe Backstitch-
        Docstring in core/backstitch_manager.py) -- der Spiegel-Mittelpunkt
        liegt daher bei pattern.width/pattern.height (nicht /2 wie bei
        ganzen Stich-Zellen) und braucht keinen "+0.5"-Rundungsversatz, weil
        Eck-Koordinaten schon exakt auf dem Gitter liegen (mirror = 2*width
        - x). Beide Endpunkte werden IMMER mit derselben Transformation
        gespiegelt (nie unabhängig!), sonst würde aus einer geraden Linie
        ein irreführendes, verdrehtes Liniensegment.

        Bewusst nur Horizontal/Vertikal/Quad + die Legacy-Booleans
        unterstützt (Oktal degradiert wie beim Punkt-Pendant auf Quad) --
        eine echte Diagonal-Spiegelung für LINIEN ist ein deutlich härteres
        Geometrie-Problem als für einzelne Punkte (die Steigung dreht sich
        mit, nicht nur die Position), analog zur bereits etablierten
        Oktal-Rechteck-Einschränkung bleibt das hier bewusst außen vor.
        """
        if not self._pattern:
            return [(x1, y1, x2, y2)]

        max_x = 2 * self._pattern.width
        max_y = 2 * self._pattern.height
        lines = {(x1, y1, x2, y2)}

        def _in_bounds(px1: int, py1: int, px2: int, py2: int) -> bool:
            return (
                0 <= px1 <= max_x and 0 <= py1 <= max_y and 0 <= px2 <= max_x and 0 <= py2 <= max_y
            )

        mode = self._mirror_mode
        mirror_h = mode in (MirrorMode.HORIZONTAL, MirrorMode.QUAD, MirrorMode.OCTAL) or (
            mode == MirrorMode.NONE and self._mirror_horizontal
        )
        mirror_v = mode in (MirrorMode.VERTICAL, MirrorMode.QUAD, MirrorMode.OCTAL) or (
            mode == MirrorMode.NONE and self._mirror_vertical
        )

        if mirror_h:
            mx1, mx2 = max_x - x1, max_x - x2
            if _in_bounds(mx1, y1, mx2, y2):
                lines.add((mx1, y1, mx2, y2))
        if mirror_v:
            my1, my2 = max_y - y1, max_y - y2
            if _in_bounds(x1, my1, x2, my2):
                lines.add((x1, my1, x2, my2))
        if mirror_h and mirror_v:
            mx1, mx2 = max_x - x1, max_x - x2
            my1, my2 = max_y - y1, max_y - y2
            if _in_bounds(mx1, my1, mx2, my2):
                lines.add((mx1, my1, mx2, my2))

        return list(lines)

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
            row = [(layer.get_stitch(x, y), layer.get_stitch_type(x, y)) for x in range(x1, x2 + 1)]
            data.append(row)

        for y_idx, row in enumerate(data):
            row.reverse()
            for x_idx, (color_idx, stitch_type) in enumerate(row):
                x, y = x1 + x_idx, y1 + y_idx
                if color_idx is not None:
                    # Diagonale Halb-/Viertelstiche drehen bei horizontaler
                    # Spiegelung ihre Ausrichtung mit (z.B. "/" -> "\"),
                    # analog zum mirror_horizontal-Plugin und
                    # ROTATE_CW_MAP/FLIP_V_MAP fuer die Geschwister-Ops.
                    layer.set_stitch(
                        x, y, color_idx, stitch_type=FLIP_H_MAP.get(stitch_type, stitch_type)
                    )
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
            row = [(layer.get_stitch(x, y), layer.get_stitch_type(x, y)) for x in range(x1, x2 + 1)]
            data.append(row)

        data.reverse()
        for y_idx, row in enumerate(data):
            for x_idx, (color_idx, stitch_type) in enumerate(row):
                x, y = x1 + x_idx, y1 + y_idx
                if color_idx is not None:
                    layer.set_stitch(
                        x, y, color_idx, stitch_type=FLIP_V_MAP.get(stitch_type, stitch_type)
                    )
                else:
                    layer.remove_stitch(x, y)

        return True
