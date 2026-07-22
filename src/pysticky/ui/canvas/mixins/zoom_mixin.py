"""
Zoom-Mixin für Canvas.

Enthält alle Zoom-Funktionen.
"""

from typing import TYPE_CHECKING

from ....utils import clamp_int

if TYPE_CHECKING:
    from ..canvas import CrossStitchCanvas


class ZoomMixin:
    """Mixin für Zoom-Funktionalität."""

    def zoom_in(
        self: "CrossStitchCanvas", anchor_x: int | None = None, anchor_y: int | None = None
    ) -> None:
        """Vergrößert die Ansicht multiplikativ um ZOOM_STEP (mind. +1px,
        damit kleine Zellgrößen bei ZOOM_STEP nahe 1.0 nicht steckenbleiben).

        anchor_x/anchor_y: Bildschirm-Koordinate, die beim Zoomen an
        derselben Stelle bleiben soll (z.B. Mausposition beim Mausrad-Zoom).
        None (Default) = Canvas-Mitte, wie bisher.
        """
        target = max(self._cell_size + 1, round(self._cell_size * self.ZOOM_STEP))
        self._set_cell_size(min(target, self.MAX_CELL_SIZE), anchor_x, anchor_y)

    def zoom_out(
        self: "CrossStitchCanvas", anchor_x: int | None = None, anchor_y: int | None = None
    ) -> None:
        """Verkleinert die Ansicht multiplikativ um ZOOM_STEP (mind. -1px).

        anchor_x/anchor_y: siehe zoom_in().
        """
        target = min(self._cell_size - 1, round(self._cell_size / self.ZOOM_STEP))
        self._set_cell_size(max(target, self.MIN_CELL_SIZE), anchor_x, anchor_y)

    def zoom_fit(self: "CrossStitchCanvas") -> None:
        """Passt die Ansicht an das Fenster an."""
        if not self._pattern:
            return

        available_width = self.width() - 40
        available_height = self.height() - 40

        cell_w = available_width // self._pattern.width
        cell_h = available_height // self._pattern.height

        new_size = max(self.MIN_CELL_SIZE, min(cell_w, cell_h, self.MAX_CELL_SIZE))
        self._set_cell_size(new_size)
        self._center_pattern()

    def zoom_reset(self: "CrossStitchCanvas") -> None:
        """Setzt den Zoom auf 100% zurück."""
        # Anders als set_zoom() clampte dies bisher NICHT gegen
        # MIN_CELL_SIZE/MAX_CELL_SIZE -- wenn Einstellungen -> Canvas ->
        # Zoom so konfiguriert ist, dass DEFAULT_CELL_SIZE ausserhalb der
        # (unabhaengig einstellbaren) Min/Max-Grenzen liegt, ueberschritt
        # Zoom-Reset (100%) diese Grenzen still, bis der naechste
        # zoom_in()/zoom_out()-Schritt wieder korrekt clampte.
        target = clamp_int(self.DEFAULT_CELL_SIZE, self.MIN_CELL_SIZE, self.MAX_CELL_SIZE)
        self._set_cell_size(target)
        self._center_pattern()

    def set_zoom(self: "CrossStitchCanvas", factor: float) -> None:
        """Setzt den Zoom-Faktor (1.0 = 100%)."""
        # round() statt int(): int() rundet immer Richtung 0 ab, z.B.
        # factor=1.33 -> int(26.6)=26 statt der naheliegenden 27 -- dadurch
        # zeigte get_zoom_percent() danach 130% statt der angefragten 133%,
        # kein sauberer Roundtrip zwischen set_zoom()/get_zoom_percent().
        new_size = round(self.DEFAULT_CELL_SIZE * factor)
        new_size = clamp_int(new_size, self.MIN_CELL_SIZE, self.MAX_CELL_SIZE)
        self._set_cell_size(new_size)

    def get_zoom_percent(self: "CrossStitchCanvas") -> float:
        """Gibt den aktuellen Zoom in Prozent zurück."""
        return (self._cell_size / self.DEFAULT_CELL_SIZE) * 100.0

    def _set_cell_size(
        self: "CrossStitchCanvas",
        size: int,
        anchor_x: int | None = None,
        anchor_y: int | None = None,
    ) -> None:
        """Setzt die Zellgröße und aktualisiert die Ansicht.

        anchor_x/anchor_y: Bildschirm-Koordinate, die beim Zoomen an
        derselben Stelle bleiben soll ("Zoom zu Cursor"). None (Default) =
        Canvas-Mitte -- so bleiben zoom_reset()/zoom_fit()/set_zoom()
        weiterhin zentriert, nur zoom_in()/zoom_out() (Mausrad) reichen
        bewusst einen Anker durch.
        """
        old_size = self._cell_size
        self._cell_size = size

        if size != old_size:
            # Gecachte Chunk-Pixmaps (OptimizedCrossStitchCanvas) sind bei der
            # alten Zellgröße gerendert -- der Cache-Key kennt nur
            # (chunk_x, chunk_y), nicht cell_size. Ohne Invalidierung würde
            # nach dem Zoomen ein alt-skalierter Pixmap an der neuen
            # Bildschirmposition gezeichnet: falsch große, verschobene Blöcke.
            self.invalidate_all()

        if self._pattern:
            anchor_screen_x = self.width() // 2 if anchor_x is None else anchor_x
            anchor_screen_y = self.height() // 2 if anchor_y is None else anchor_y

            grid_x = (anchor_screen_x - self._offset_x) / old_size
            grid_y = (anchor_screen_y - self._offset_y) / old_size

            self._offset_x = int(anchor_screen_x - grid_x * self._cell_size)
            self._offset_y = int(anchor_screen_y - grid_y * self._cell_size)

        self.zoom_changed.emit(self._cell_size / self.DEFAULT_CELL_SIZE)
        self.offset_changed.emit(self._offset_x, self._offset_y)
        self.update()
