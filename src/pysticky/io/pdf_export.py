"""
PDF-Export für Kreuzstich-Muster.

Erstellt druckfertige PDF-Dateien mit:
- Deckblatt mit Vorschau und Statistiken
- Farbvorschau des fertigen Musters
- Legende mit Garnbedarf
- Übersichtskarte der Seiten
- Musterseiten (40x40 Stiche pro Seite)

Benötigt: reportlab (`pip install reportlab`)
"""

import logging
from datetime import datetime
from math import ceil
from pathlib import Path
from typing import TYPE_CHECKING

from ..utils.logging import get_logger

logger = get_logger(__name__)

from .export_cache import CompositeGridCache
from .export_common import (
    count_page_colors,
    get_pixel_color,
    get_pixel_stitch_type,
    get_pixel_symbol,
)
from .pdf_export_drawings import PDFDrawingsMixin
from .pdf_export_sections import PDFSectionsMixin

if TYPE_CHECKING:
    from ..core import ColorPath, OptimizationResult, Pattern

# Optionale Abhängigkeit
try:
    from reportlab.graphics import renderPDF
    from reportlab.graphics.shapes import Drawing, Line, Rect, String
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A0, A1, A2, A3, A4, LETTER, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm, mm
    from reportlab.pdfgen import canvas as pdfcanvas
    from reportlab.platypus import (
        Image,
        KeepTogether,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def check_reportlab_available() -> bool:
    """Prüft ob reportlab installiert ist."""
    return REPORTLAB_AVAILABLE


class PDFExporter(PDFDrawingsMixin, PDFSectionsMixin):
    """Exportiert Kreuzstich-Muster als PDF-Datei."""

    # Verfügbare Papierformate: Name → (pagesize, Stiche X, Stiche Y).
    # A1/A0 sind hauptsächlich für DP-1:1-Druck — bei 200x200 Drills mit
    # 2.5mm Pitch braucht man mindestens A2, für eine einzelne Seite A1/A0.
    PAGE_FORMATS = (
        {
            "A4": {"pagesize": A4, "stitches_x": 40, "stitches_y": 40, "margin": 15},
            "A3": {"pagesize": A3, "stitches_x": 60, "stitches_y": 60, "margin": 15},
            "A2": {"pagesize": A2, "stitches_x": 90, "stitches_y": 90, "margin": 20},
            "A1": {"pagesize": A1, "stitches_x": 130, "stitches_y": 130, "margin": 20},
            "A0": {"pagesize": A0, "stitches_x": 190, "stitches_y": 190, "margin": 25},
            "Letter": {"pagesize": LETTER, "stitches_x": 40, "stitches_y": 40, "margin": 15},
        }
        if REPORTLAB_AVAILABLE
        else {}
    )

    # Stiche pro Strang je nach Stofftyp
    STITCHES_PER_SKEIN = {
        11: 2500,
        14: 1800,
        16: 1600,
        18: 1400,
        22: 1200,
        28: 1000,
        32: 800,
    }

    def __init__(
        self,
        pattern: "Pattern",
        include_path_preview: bool = True,
        page_format: str = "A4",
        notes: str = "",
        cross_ref_palettes: list[str] | None = None,
        page_overlap_stitches: int = 0,
        password: str | None = None,
        watermark_text: str | None = None,
        allow_printing: bool = True,
        allow_copying: bool = True,
        mystery_mode: bool = False,
        cells_per_page: int | None = None,
    ) -> None:
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "reportlab ist nicht installiert. Bitte installieren mit: pip install reportlab"
            )

        self.pattern = pattern
        # Mystery-Modus: Musterseiten + Vorschau ohne Farben (nur Symbole
        # + Gitter) für Überraschungs-Kits. Legende bleibt unverändert.
        self.mystery_mode = mystery_mode
        self._color_stats: list[dict] = []
        self._total_stitches = 0
        self._total_skeins = 0
        self._cache: CompositeGridCache | None = None
        self._styles = getSampleStyleSheet()
        self._setup_styles()

        # Papierformat konfigurieren
        fmt = self.PAGE_FORMATS.get(page_format, self.PAGE_FORMATS["A4"])
        self._pagesize = fmt["pagesize"]
        self._margin = fmt["margin"] * mm
        self._page_format_name = page_format

        # Verfügbare Zeichenfläche berechnen
        page_w, page_h = self._pagesize
        self._available_width = page_w - 2 * self._margin
        self._available_height = page_h - 2 * self._margin

        # DP-Modus: 1:1-Druck-Massstab. Drill-Pitch (2.5/2.8/3.0 mm laut
        # Drill-Raster-Auswahl) bestimmt die Cell-Size auf dem Druckblatt,
        # NICHT die feste 40-Drills-Vorgabe. So passt der echte Drill in
        # die ausgedruckte Klebefolien-Zelle.
        #
        # Wir reservieren großzügig für Header (Spalten-/Zeilen-Nummern
        # 8mm), Page-Title/Info-Block oben (~15mm) und Mini-Legend unten
        # (~20mm) — insgesamt grob 45mm. Sonst kollidiert das Drawing mit
        # dem Frame-Rand und reportlab wirft LayoutError.
        from .export_common import drill_pitch_mm, is_diamond_mode

        self._dp_cell_size: float | None = None
        if is_diamond_mode(self.pattern):
            pitch = drill_pitch_mm(self.pattern) * mm
            self._dp_cell_size = pitch
            width_reserve = 12 * mm  # Header-Spalte links + Sicherheit
            height_reserve = 50 * mm  # Page-Header oben + Mini-Legend unten
            stitches_x = int((self._available_width - width_reserve) / pitch)
            stitches_y = int((self._available_height - height_reserve) / pitch)
            self.STITCHES_PER_PAGE_X = max(1, stitches_x)
            self.STITCHES_PER_PAGE_Y = max(1, stitches_y)
        else:
            # cells_per_page (Einstellungen → Dateien → "Zellen/Seite")
            # ueberschreibt die Format-Vorgabe uniform -- nur fuer normale
            # Kreuzstich-Seiten sinnvoll; der DP-1:1-Druckmassstab oben
            # bleibt physikalisch an den Drill-Pitch gebunden.
            self.STITCHES_PER_PAGE_X = cells_per_page or fmt["stitches_x"]
            self.STITCHES_PER_PAGE_Y = cells_per_page or fmt["stitches_y"]

        self._notes = notes

        # Stickpfad-Optimierung
        self._include_path_preview = include_path_preview
        self._optimization_result: "OptimizationResult | None" = None

        # Optionale Hersteller-Cross-Reference für die Legende
        self.cross_ref_palettes: list[str] = cross_ref_palettes or []

        # Working-Chart-Pages: Overlap-Stiche an jeder Seite rechts/unten
        self.page_overlap_stitches: int = max(0, int(page_overlap_stitches))

        # PDF-Schutz: optionales Password und Wasserzeichen
        self.password: str | None = password or None
        self.watermark_text: str | None = (watermark_text or "").strip() or None
        self.allow_printing: bool = bool(allow_printing)
        self.allow_copying: bool = bool(allow_copying)

    def _setup_styles(self) -> None:
        """Erstellt benutzerdefinierte Styles."""
        self._styles.add(
            ParagraphStyle(
                "Title1",
                parent=self._styles["Heading1"],
                fontSize=24,
                alignment=TA_CENTER,
                spaceAfter=12,
                textColor=colors.HexColor("#333333"),
            )
        )
        self._styles.add(
            ParagraphStyle(
                "Title2",
                parent=self._styles["Heading2"],
                fontSize=16,
                alignment=TA_CENTER,
                spaceAfter=8,
                textColor=colors.HexColor("#555555"),
            )
        )
        self._styles.add(
            ParagraphStyle(
                "CenterText",
                parent=self._styles["Normal"],
                alignment=TA_CENTER,
                fontSize=10,
            )
        )
        self._styles.add(
            ParagraphStyle(
                "SmallCenter",
                parent=self._styles["Normal"],
                alignment=TA_CENTER,
                fontSize=8,
                textColor=colors.HexColor("#666666"),
            )
        )

    def export(self, filepath: str | Path) -> bool:
        """Exportiert das Muster als PDF-Datei."""
        filepath = Path(filepath)
        if not filepath.suffix.lower() == ".pdf":
            filepath = filepath.with_suffix(".pdf")

        # Statistiken berechnen
        self._calculate_statistics()

        # Komposit-Grid einmalig pre-computen — alle Per-Pixel-Lookups
        # gehen anschliessend über den Cache statt durch den Layer-Stack.
        self._cache = CompositeGridCache(self.pattern)

        # Stickpfade berechnen wenn gewünscht
        if self._include_path_preview:
            self._calculate_stitch_paths()

        # Seitenaufteilung
        pages_x = ceil(self.pattern.width / self.STITCHES_PER_PAGE_X)
        pages_y = ceil(self.pattern.height / self.STITCHES_PER_PAGE_Y)
        total_pages = pages_x * pages_y

        # Titel und Datum
        title = filepath.stem
        date = datetime.now().strftime("%d.%m.%Y")

        # Physische Größe
        stitches_per_cm = self.pattern.fabric_count / 2.54
        phys_width = self.pattern.width / stitches_per_cm
        phys_height = self.pattern.height / stitches_per_cm

        try:
            # PDF erstellen — mit optionalem Schutz
            doc_kwargs = {
                "pagesize": self._pagesize,
                "rightMargin": self._margin,
                "leftMargin": self._margin,
                "topMargin": self._margin,
                "bottomMargin": self._margin,
            }
            if self.password:
                # reportlab StandardEncryption: setzt Open-Password und
                # konfiguriert die User-Permissions
                from reportlab.lib.pdfencrypt import StandardEncryption

                doc_kwargs["encrypt"] = StandardEncryption(
                    userPassword=self.password,
                    ownerPassword=self.password,
                    canPrint=1 if self.allow_printing else 0,
                    canModify=0,
                    canCopy=1 if self.allow_copying else 0,
                    canAnnotate=0,
                    strength=128,
                )
            doc = SimpleDocTemplate(str(filepath), **doc_kwargs)

            story = []

            # Deckblatt
            story.extend(self._create_cover(title, date, phys_width, phys_height, total_pages))
            story.append(PageBreak())

            # Notizen (optional)
            if self._notes.strip():
                from ..core.i18n import t

                story.append(Paragraph(t("Notizen"), self._styles["Title2"]))
                story.append(Spacer(1, 6 * mm))
                for line in self._notes.strip().split("\n"):
                    story.append(Paragraph(line or "&nbsp;", self._styles["Normal"]))
                story.append(PageBreak())

            # Vorschau
            story.extend(self._create_preview(title, phys_width, phys_height))
            story.append(PageBreak())

            # Legende
            story.extend(self._create_legend())
            story.append(PageBreak())

            # Übersicht
            story.extend(self._create_overview(pages_x, pages_y))
            story.append(PageBreak())

            # Musterseiten
            for page_num in range(total_pages):
                story.extend(
                    self._create_pattern_page(page_num, pages_x, pages_y, total_pages, title, date)
                )
                if page_num < total_pages - 1:
                    story.append(PageBreak())

            # Page-Footer mit Copyright (falls gesetzt)
            from .export_common import get_watermark

            _author, copyright_ = get_watermark(self.pattern)

            watermark_text = self.watermark_text

            def _draw_footer(canvas, _doc):
                # Footer mit Copyright
                if copyright_:
                    canvas.saveState()
                    canvas.setFont("Helvetica", 8)
                    canvas.setFillColor(colors.HexColor("#888888"))
                    page_w = self._pagesize[0]
                    canvas.drawCentredString(page_w / 2.0, 8 * mm, copyright_)
                    canvas.restoreState()

                # Wasserzeichen — gross, diagonal, semi-transparent
                if watermark_text:
                    canvas.saveState()
                    page_w, page_h = self._pagesize
                    canvas.translate(page_w / 2.0, page_h / 2.0)
                    canvas.rotate(45)
                    canvas.setFillColor(colors.HexColor("#cccccc"))
                    canvas.setFillAlpha(0.35)
                    canvas.setFont("Helvetica-Bold", 60)
                    canvas.drawCentredString(0, 0, watermark_text)
                    canvas.restoreState()

            # PDF generieren
            doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
            return True

        except OSError as e:
            logger.error("Fehler beim PDF-Export: %s", e, exc_info=True)
            raise

    def _calculate_statistics(self) -> None:
        """Berechnet Farbstatistiken und Garnbedarf.

        Verwendet iterate_composite_stitches(), damit nur sichtbare Layer
        berücksichtigt werden und bei Überlappungen nur der oberste Stich zählt.
        """
        self._color_stats = []
        stitch_counts: dict[int, int] = {}

        # Stiche pro Farbe zählen (nur sichtbare Layer, oberster Stich)
        for _x, _y, color_idx in self.pattern.iterate_composite_stitches():
            stitch_counts[color_idx] = stitch_counts.get(color_idx, 0) + 1

        stitches_per_skein = self.STITCHES_PER_SKEIN.get(self.pattern.fabric_count, 1800)
        # Modus-spezifischer "Bedarf"-Wert (gleiche Logik wie HTML-Export):
        # Stitch -> Stränge, Diamond -> Drill-Anzahl + 10% Reserve.
        is_dp = getattr(self.pattern, "mode", "stitch") == "diamond"

        self._total_stitches = 0
        self._total_skeins = 0
        self._stitches_to_do = 0  # Stiche ohne übersprungene Farben
        self._skipped_colors = 0

        for i, entry in enumerate(self.pattern.color_entries):
            count = stitch_counts.get(i, 0)
            skip = entry.skip_stitching

            # Bead-Farben: kein Strang-Bedarf, eigene Sektion
            if entry.is_bead:
                self._color_stats.append(
                    {
                        "index": i,
                        "symbol": entry.symbol,
                        "thread": entry.thread,
                        "count": count,
                        "skeins": 0,
                        "skip": skip,
                        "is_bead": True,
                    }
                )
                continue

            # Stränge / Drill-Anzahl nur für nicht-übersprungene Farben berechnen
            if skip:
                skeins = 0
                if count > 0:
                    self._skipped_colors += 1
            elif is_dp:
                skeins = int(count * 1.10) if count > 0 else 0
                self._stitches_to_do += count
            else:
                skeins = ceil(count / stitches_per_skein) if count > 0 else 0
                if count > 1000:
                    skeins += 1
                self._stitches_to_do += count

            self._color_stats.append(
                {
                    "index": i,
                    "symbol": entry.symbol,
                    "thread": entry.thread,
                    "count": count,
                    "skeins": skeins,
                    "skip": skip,
                    "is_bead": False,
                }
            )

            self._total_stitches += count
            self._total_skeins += skeins

    def _calculate_stitch_paths(self) -> None:
        """Berechnet optimierte Stickpfade für alle Farben."""
        try:
            from ..core import OptimizationStrategy, StitchPathOptimizer

            optimizer = StitchPathOptimizer(self.pattern)
            self._optimization_result = optimizer.optimize(
                OptimizationStrategy.NEAREST_NEIGHBOR, self.pattern.fabric_count
            )
        except ImportError:
            # StitchPathOptimizer nicht verfügbar
            self._optimization_result = None
        except (ValueError, RuntimeError) as e:
            logger.warning("Fehler bei Stickpfad-Berechnung: %s", e)
            self._optimization_result = None

    def _get_page_color_paths(
        self, start_x: int, start_y: int, end_x: int, end_y: int
    ) -> list["ColorPath"]:
        """
        Gibt die Farbpfade zurück, gefiltert auf einen Seitenbereich.
        Enthält nur Stiche, die innerhalb des Bereichs liegen.
        """
        if not self._optimization_result:
            return []

        from ..core import ColorPath as CP
        from ..core import StitchStep

        page_paths = []

        for orig_path in self._optimization_result.color_paths:
            # Stiche filtern, die im Seitenbereich liegen
            page_steps: list = []
            for step in orig_path.steps:
                if start_x <= step.x <= end_x and start_y <= step.y <= end_y:
                    # Relativer Step für die Seite
                    rel_step = StitchStep(
                        x=step.x - start_x,
                        y=step.y - start_y,
                        color_index=step.color_index,
                        step_number=len(page_steps) + 1,
                        distance_from_prev=step.distance_from_prev,
                        is_jump=step.is_jump,
                    )
                    page_steps.append(rel_step)

            if page_steps:
                # Distanzen neu berechnen für Seitenbereich
                total_dist = 0
                jump_count = 0
                prev_step = None
                for i, step in enumerate(page_steps):
                    if prev_step:
                        dx = step.x - prev_step.x
                        dy = step.y - prev_step.y
                        dist = (dx * dx + dy * dy) ** 0.5
                        step.distance_from_prev = dist
                        step.is_jump = dist > 4
                        total_dist += dist
                        if step.is_jump:
                            jump_count += 1
                    else:
                        step.distance_from_prev = 0
                        step.is_jump = False
                    prev_step = step

                page_path = CP(
                    color_index=orig_path.color_index,
                    steps=page_steps,
                    total_distance=total_dist,
                    jump_count=jump_count,
                    stitch_count=len(page_steps),
                )
                page_paths.append(page_path)

        return page_paths

    def _count_page_colors(
        self, start_x: int, start_y: int, end_x: int, end_y: int
    ) -> dict[int, int]:
        """Zählt Farben auf einer Seite (oberstes sichtbares Layer gewinnt)."""
        if self._cache is not None:
            return self._cache.count_page_colors(start_x, start_y, end_x, end_y)
        return count_page_colors(self.pattern, start_x, start_y, end_x, end_y)

    def _get_pixel_color(self, x: int, y: int) -> tuple[int, int, int] | None:
        """Gibt die Farbe an einer Position zurück (oberstes sichtbares Layer)."""
        if self._cache is not None:
            return self._cache.get_color(x, y)
        return get_pixel_color(self.pattern, x, y)

    def _get_pixel_symbol(self, x: int, y: int) -> str:
        """Gibt das Symbol an einer Position zurück (oberstes sichtbares Layer)."""
        if self._cache is not None:
            return self._cache.get_symbol(x, y)
        return get_pixel_symbol(self.pattern, x, y)

    def _get_pixel_stitch_type(self, x: int, y: int) -> int:
        """Stitch-Type an einer Position (oberstes sichtbares Layer)."""
        if self._cache is not None:
            return self._cache.get_stitch_type(x, y)
        return get_pixel_stitch_type(self.pattern, x, y)


def export_pdf(
    pattern: "Pattern",
    filepath: str | Path,
    include_path_preview: bool = True,
    page_format: str = "A4",
) -> bool:
    """
    Exportiert ein Muster als PDF.

    Args:
        pattern: Das zu exportierende Muster
        filepath: Ziel-Pfad für die PDF-Datei
        include_path_preview: Ob Stickpfad-Preview auf jeder Seite angezeigt werden soll
        page_format: Papierformat ("A4", "A3", "A2", "Letter")

    Returns:
        True bei Erfolg, False bei Fehler
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("PDF-Export benötigt reportlab. Installieren mit: pip install reportlab")

    exporter = PDFExporter(
        pattern, include_path_preview=include_path_preview, page_format=page_format
    )
    return exporter.export(filepath)
