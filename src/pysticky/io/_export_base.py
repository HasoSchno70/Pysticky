"""
Typing-Basen für die Export-Mixins — NUR für die statische Prüfung.

Die HTML-/PDF-Exporter sind aus Mixins zusammengesetzt; die Mixins greifen
auf Attribute und Methoden zu, die erst die konkrete Exporter-Klasse setzt
bzw. definiert (z.B. `self.pattern`, `self._get_pixel_color(...)`). mypy
prüft jedes Mixin isoliert und sieht diese nicht — daher früher ~216
[attr-defined]-Fehler.

Diese Basen deklarieren das geteilte Interface. Sie werden NUR unter
`TYPE_CHECKING` als Mixin-Basisklasse eingehängt (siehe `_export_typing`
in den Mixin-Modulen); zur Laufzeit erben die Mixins weiter `object` —
es gibt also KEINEN Verhaltensunterschied.

Attribut-/Methodentypen sind bewusst großzügig (`Any`), wo sie nur als
Existenz-Nachweis dienen; die konkreten Exporter liefern die echten
Signaturen, ihre Overrides sind gegen `Any` immer kompatibel.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..core import Pattern
    from .export_cache import CompositeGridCache


class _ExportBase:
    """Gemeinsames Interface von HTML- und PDF-Exporter."""

    pattern: Pattern
    _cache: CompositeGridCache | None
    _color_stats: list[dict]
    _total_stitches: int
    _total_skeins: int
    STITCHES_PER_PAGE_X: int
    STITCHES_PER_PAGE_Y: int

    def _get_pixel_color(self, x: Any, y: Any) -> Any: ...
    def _get_pixel_symbol(self, x: Any, y: Any) -> Any: ...
    def _get_pixel_stitch_type(self, x: Any, y: Any) -> Any: ...
    def _count_page_colors(self, start_x: Any, start_y: Any, end_x: Any, end_y: Any) -> Any: ...


class _HTMLExportBase(_ExportBase):
    """Zusatz-Interface, das die HTML-Mixins voraussetzen."""

    def _generate_backstitches_svg(
        self,
        cell_size: Any,
        offset_x: Any = ...,
        offset_y: Any = ...,
        start_stitch_x: Any = ...,
        start_stitch_y: Any = ...,
        end_stitch_x: Any = ...,
        end_stitch_y: Any = ...,
    ) -> Any: ...
    def _generate_partial_stitches_svg(
        self,
        cell_size: Any,
        offset_x: Any,
        offset_y: Any,
        start_stitch_x: Any,
        start_stitch_y: Any,
        end_stitch_x: Any,
        end_stitch_y: Any,
    ) -> Any: ...
    def _get_page_backstitches(self, start_x: Any, start_y: Any, end_x: Any, end_y: Any) -> Any: ...


class _PDFExportBase(_ExportBase):
    """Zusatz-Interface, das die PDF-Mixins voraussetzen."""

    _styles: Any
    _skipped_colors: int
    _stitches_to_do: int
    _available_width: float
    _available_height: float
    _page_format_name: str
    _optimization_result: Any
    _include_path_preview: bool

    def _create_preview_drawing(self, max_width: Any, max_height: Any) -> Any: ...
    def _create_pattern_drawing_with_paths(
        self, start_x: Any, start_y: Any, end_x: Any, end_y: Any, page_paths: Any
    ) -> Any: ...
    def _get_page_color_paths(self, start_x: Any, start_y: Any, end_x: Any, end_y: Any) -> Any: ...
