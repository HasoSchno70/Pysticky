"""
Sektions-Mixin für den PDF-Export.

Enthält Methoden zur Erstellung der einzelnen PDF-Abschnitte:
Deckblatt, Vorschau, Legende, Übersicht und Musterseiten.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    from reportlab.graphics.shapes import Drawing, Line
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

if TYPE_CHECKING:
    from ._export_base import _PDFExportBase as _Base
else:
    _Base = object


class PDFSectionsMixin(_Base):
    """Mixin mit Sektions-Methoden für den PDF-Export."""

    def _create_cover(
        self, title: str, date: str, phys_width: float, phys_height: float, total_pages: int
    ) -> list:
        """Erstellt das Deckblatt."""
        elements = []

        from ..core.i18n import t
        from .export_common import is_diamond_mode

        is_dp = is_diamond_mode(self.pattern)

        elements.append(Spacer(1, 30 * mm))

        # Titel — modusabhaengig, wie beim HTML-Export (html_export_sections.py)
        cover_title = t("💎 DIAMOND-PAINTING-VORLAGE") if is_dp else t("✂ KREUZSTICH-MUSTER")
        elements.append(Paragraph(cover_title, self._styles["Title1"]))
        elements.append(Paragraph(title, self._styles["Title2"]))

        # Wasserzeichen (Author + Copyright)
        from .export_common import get_watermark

        author, copyright_ = get_watermark(self.pattern)
        if author:
            elements.append(
                Paragraph(t("von {author}").format(author=author), self._styles["CenterText"])
            )

        elements.append(
            Paragraph(t("Erstellt am {date}").format(date=date), self._styles["SmallCenter"])
        )
        if copyright_:
            elements.append(Paragraph(copyright_, self._styles["SmallCenter"]))

        elements.append(Spacer(1, 15 * mm))

        # Vorschau-Bild (dynamisch: 80% der verfügbaren Breite)
        preview_w = self._available_width * 0.8
        preview_h = min(preview_w * 0.66, self._available_height * 0.35)
        preview = self._create_preview_drawing(preview_w, preview_h)
        if preview:
            elements.append(preview)

        elements.append(Spacer(1, 15 * mm))

        # Info-Tabelle (Terminologie aus export_common)
        from .export_common import fabric_label_for, terms_for

        terms = terms_for(self.pattern)
        fabric_name = fabric_label_for(self.pattern)
        # Mystery-Modus: die reine Rückstich-ANZAHL verrät schon Konturen des
        # Motivs, genau wie beim HTML-Export (html_export_sections.py) ---
        # deshalb hier ebenfalls unterdrücken, nicht nur im DP-Modus.
        mystery_mode = getattr(self, "mystery_mode", False)
        backstitch_count = 0 if (is_dp or mystery_mode) else len(self.pattern.backstitches)

        # Farben-Info mit übersprungenen
        colors_text = t("{n} verschiedene").format(n=len(self._color_stats))
        if self._skipped_colors > 0:
            skip_label = t("nicht kleben") if is_dp else t("nicht sticken")
            colors_text += f" ({self._skipped_colors} {skip_label})"

        unit_label = terms["unit_plural"]
        if self._skipped_colors > 0:
            stitches_text = t("{count} {unit} (+ {extra} Stofffarbe)").format(
                count=self._stitches_to_do,
                unit=unit_label,
                extra=self._total_stitches - self._stitches_to_do,
            )
        else:
            stitches_text = t("{count} {unit}").format(count=self._total_stitches, unit=unit_label)

        info_data = [
            [
                t("Mustergröße"),
                t("{w} × {h} {unit}").format(
                    w=self.pattern.width, h=self.pattern.height, unit=unit_label
                ),
            ],
            [terms["fabric_label"], fabric_name],
            [
                t("Fertige Größe"),
                t("{w} × {h} cm").format(w=f"{phys_width:.1f}", h=f"{phys_height:.1f}"),
            ],
            [t("Anzahl Farben"), colors_text],
            [
                t("Gesamt-{unit}").format(unit=unit_label),
                stitches_text,
            ],
            [
                terms["supply_label"],
                t("ca. {n} {unit}").format(n=self._total_skeins, unit=terms["supply_unit"]),
            ],
            [t("Musterseiten"), t("{n} Seiten").format(n=total_pages)],
        ]

        if backstitch_count > 0:
            info_data.insert(5, [t("Rückstiche"), t("{n} Linien").format(n=backstitch_count)])

        table = Table(info_data, colWidths=[60 * mm, 80 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f4ff")),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#667eea")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        elements.append(table)

        return elements

    def _create_preview(self, title: str, phys_width: float, phys_height: float) -> list:
        """Erstellt die Vorschau-Seite."""
        from ..core.i18n import t
        from .export_common import fabric_label_for, is_diamond_mode, terms_for

        terms = terms_for(self.pattern)
        is_dp = is_diamond_mode(self.pattern)

        elements = []
        elements.append(Paragraph(terms["preview_caption"], self._styles["Title1"]))

        fabric_name = fabric_label_for(self.pattern)
        elements.append(
            Paragraph(
                t("Fertige Größe auf {fabric}: {w} × {h} cm").format(
                    fabric=fabric_name, w=f"{phys_width:.1f}", h=f"{phys_height:.1f}"
                ),
                self._styles["CenterText"],
            )
        )

        elements.append(Spacer(1, 10 * mm))

        # Große Vorschau (dynamisch an Seitengröße angepasst)
        preview = self._create_preview_drawing(
            self._available_width - 5 * mm,
            self._available_height - 40 * mm,
        )
        if preview:
            elements.append(preview)

        # Rückstich-Hinweis nur im Stick-Modus, und nicht im Mystery-Modus
        # (die Anzahl allein wuerde schon Konturen des Motivs verraten).
        if not is_dp and not getattr(self, "mystery_mode", False) and self.pattern.backstitches:
            elements.append(Spacer(1, 5 * mm))
            elements.append(
                Paragraph(
                    t("Rückstiche: {n} Linien werden über dem Muster gezeigt.").format(
                        n=len(self.pattern.backstitches)
                    ),
                    self._styles["SmallCenter"],
                )
            )

        return elements

    def _create_legend(self) -> list:
        """Erstellt die Legende."""
        from ..core.i18n import t
        from .export_common import is_diamond_mode, terms_for

        terms = terms_for(self.pattern)
        is_dp = is_diamond_mode(self.pattern)

        elements = []
        elements.append(
            Paragraph(
                t("Drill-Legende und Material") if is_dp else t("Legende und Materialbedarf"),
                self._styles["Title1"],
            )
        )

        # Beads in eigene Sektion ausgliedern, nicht in der Haupttabelle
        thread_stats = [s for s in self._color_stats if not s.get("is_bead", False)]
        bead_stats = [s for s in self._color_stats if s.get("is_bead", False)]

        unit_label = terms["unit_plural"]
        supply_label = terms["supply_unit"]

        # Zusammenfassung mit Info über übersprungene Farben
        summary_parts = [t("{n} Farben").format(n=len(thread_stats))]
        if self._skipped_colors > 0:
            action_verb = t("zu klebende") if is_dp else t("zu stickende")
            summary_parts.append(
                t("{count} {verb} {unit}").format(
                    count=self._stitches_to_do, verb=action_verb, unit=unit_label
                )
            )
            summary_parts.append(t("{n} Farbe(n) = Stofffarbe").format(n=self._skipped_colors))
        else:
            summary_parts.append(
                t("{count} {unit}").format(count=self._total_stitches, unit=unit_label)
            )
        summary_parts.append(
            t("ca. {n} {unit} benötigt").format(n=self._total_skeins, unit=supply_label)
        )

        elements.append(Paragraph(" · ".join(summary_parts), self._styles["CenterText"]))

        elements.append(Spacer(1, 8 * mm))

        # Hersteller-Cross-Reference
        cross_ref_palettes = getattr(self, "cross_ref_palettes", []) or []
        if cross_ref_palettes:
            from ..core.thread_cross_ref import find_equivalents

        # Tabellen-Header — Symbol-Spalte auch im DP-Modus (Drills bekommen
        # dasselbe Symbol wie Garnfarben, siehe Pattern.add_color).
        code_col = terms["code_header"]
        header = [t("Nr."), t("Sym."), t("Farbe"), code_col, t("Farbname")]
        header.extend(cross_ref_palettes)
        header.extend([unit_label, "%", supply_label])
        n_cross = len(cross_ref_palettes)

        # Daten
        data = [header]
        for i, stat in enumerate(thread_stats, 1):
            thread = stat["thread"]
            skip = stat.get("skip", False)

            # Prozent nur für nicht-übersprungene Farben
            if skip:
                percent_str = "-"
                skeins_str = "-"
                name_suffix = " [⊘]"
            else:
                percent = (
                    (stat["count"] * 100.0 / self._stitches_to_do)
                    if self._stitches_to_do > 0
                    else 0
                )
                percent_str = f"{percent:.1f}%"
                skeins_str = str(stat["skeins"])
                name_suffix = ""

            cross_cells = []
            if cross_ref_palettes:
                equivalents = find_equivalents(thread, cross_ref_palettes)
                for palette_name in cross_ref_palettes:
                    eq = equivalents.get(palette_name)
                    cross_cells.append((eq.catalog_number or eq.name) if eq else "—")

            # Tweed-Blends: beide Garnnummern in der Garnnr-Spalte
            if thread.is_blend:
                thread_label = " + ".join(
                    f"{c.manufacturer or ''} {c.catalog_number or ''}".strip()
                    for c in thread.blend_components
                )
            elif is_dp:
                # Im DP-Modus: nur die Drill-Nummer (Manufacturer ist immer
                # gleich, "DMC Diamond Painting 169" würde die Spalte sprengen
                # und in die Name-Spalte überlaufen).
                thread_label = thread.catalog_number or thread.name[:8]
            else:
                thread_label = f"{thread.manufacturer} {thread.catalog_number or ''}"

            data.append(
                [
                    str(i),
                    stat["symbol"],
                    "",  # Farbfeld via TableStyle
                    thread_label,
                    thread.name[:18] + name_suffix,
                    *cross_cells,
                    str(stat["count"]),
                    percent_str,
                    skeins_str,
                ]
            )

        # Spalten-Indices: [0:Nr, 1:Sym, 2:Farbe, 3:Code, 4:Name, cross..., stitches]
        color_col = 2
        code_col_idx = 3
        name_col = 4
        stitches_col = 5 + n_cross
        skeins_col = stitches_col + 2

        # Summenzeile passend bauen
        empty_cross = [""] * n_cross
        if self._skipped_colors > 0:
            action_label = t("Zu kleben:") if is_dp else t("Zu sticken:")
            data.append(
                [
                    "",
                    "",
                    "",
                    "",
                    action_label,
                    *empty_cross,
                    str(self._stitches_to_do),
                    "100%",
                    str(self._total_skeins),
                ]
            )
        else:
            data.append(
                [
                    "",
                    "",
                    "",
                    "",
                    t("Gesamt:"),
                    *empty_cross,
                    str(self._total_stitches),
                    "100%",
                    str(self._total_skeins),
                ]
            )

        # Spaltenbreiten je nach Modus.
        # DP: nur kurze Drill-Nummer in Code-Spalte → mehr Platz für Name.
        # Stick: "DMC 310" passt in 30mm.
        if is_dp:
            col_widths = [10 * mm, 10 * mm, 10 * mm, 18 * mm, 51 * mm]
        else:
            col_widths = [10 * mm, 10 * mm, 8 * mm, 30 * mm, 45 * mm]
        col_widths.extend([14 * mm] * n_cross)
        col_widths.extend([18 * mm, 15 * mm, 15 * mm])
        table = Table(data, colWidths=col_widths)

        # Basis-Style
        style_commands = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            # Erste Spalten zentriert (Nr + optional Sym)
            ("ALIGN", (0, 0), (color_col - 1, -1), "CENTER"),
            ("ALIGN", (stitches_col, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            # Summenzeile
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f4fc")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]

        # Farbfelder und übersprungene Farben markieren
        for i, stat in enumerate(thread_stats, 1):
            thread = stat["thread"]
            fill_color = colors.Color(
                thread.color.r / 255, thread.color.g / 255, thread.color.b / 255
            )
            style_commands.append(("BACKGROUND", (color_col, i), (color_col, i), fill_color))

            # Übersprungene Farben mit orangem Text markieren
            if stat.get("skip", False):
                style_commands.append(
                    ("TEXTCOLOR", (name_col, i), (name_col, i), colors.HexColor("#ff9800"))
                )
                style_commands.append(
                    (
                        "TEXTCOLOR",
                        (stitches_col + 1, i),
                        (skeins_col, i),
                        colors.HexColor("#999999"),
                    )
                )

        # Zebra-Streifen
        for i in range(2, len(data) - 1, 2):
            style_commands.append(
                ("BACKGROUND", (0, i), (color_col - 1, i), colors.HexColor("#f9f9f9"))
            )
            style_commands.append(
                ("BACKGROUND", (code_col_idx, i), (-1, i), colors.HexColor("#f9f9f9"))
            )

        table.setStyle(TableStyle(style_commands))
        elements.append(table)

        # Hinweis für übersprungene Farben
        if self._skipped_colors > 0:
            elements.append(Spacer(1, 3 * mm))
            elements.append(
                Paragraph(
                    f"<font size='8' color='#ff9800'>⊘ = {t('Stofffarbe, wird nicht gestickt')}</font>",
                    self._styles["Normal"],
                )
            )

        # Rückstich-Legende — im DP-Modus weglassen
        if not is_dp and self.pattern.backstitches:
            elements.append(Spacer(1, 10 * mm))
            elements.append(Paragraph(t("Rückstiche"), self._styles["Title2"]))

            bs_by_color: dict[int, int] = {}
            for bs in self.pattern.backstitches:
                bs_by_color[bs.color_index] = bs_by_color.get(bs.color_index, 0) + 1

            bs_data = [[t("Farbe"), t("Symbol"), t("Garnnummer"), t("Farbname"), t("Anzahl")]]
            for color_idx, count in sorted(bs_by_color.items()):
                entry = self.pattern.get_color_entry(color_idx)
                if entry:
                    bs_data.append(
                        [
                            "",
                            entry.symbol,
                            f"{entry.thread.manufacturer} {entry.thread.catalog_number or ''}",
                            entry.thread.name[:25],
                            str(count),
                        ]
                    )

            bs_data.append(["", "", "", t("Gesamt:"), str(len(self.pattern.backstitches))])

            bs_table = Table(bs_data, colWidths=[10 * mm, 15 * mm, 40 * mm, 55 * mm, 20 * mm])

            bs_style = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#667eea")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (1, -1), "CENTER"),
                ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f4fc")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ]

            # Farbfelder
            row = 1
            for color_idx in sorted(bs_by_color.keys()):
                entry = self.pattern.get_color_entry(color_idx)
                if entry:
                    fill = colors.Color(
                        entry.thread.color.r / 255,
                        entry.thread.color.g / 255,
                        entry.thread.color.b / 255,
                    )
                    bs_style.append(("BACKGROUND", (0, row), (0, row), fill))
                    row += 1

            bs_table.setStyle(TableStyle(bs_style))
            elements.append(bs_table)

        # Bead-Legende (Perlen)
        if bead_stats:
            elements.append(Spacer(1, 10 * mm))
            elements.append(Paragraph(t("Perlen (Beads)"), self._styles["Title2"]))

            bead_data = [[t("Farbe"), t("Symbol"), t("Perlen-Nr."), t("Farbname"), t("Anzahl")]]
            total_beads = 0
            for stat in bead_stats:
                thread = stat["thread"]
                count = stat["count"]
                total_beads += count
                bead_data.append(
                    [
                        "",
                        stat["symbol"],
                        f"{thread.manufacturer} {thread.catalog_number or ''}",
                        thread.name[:25],
                        str(count),
                    ]
                )

            bead_data.append(["", "", "", t("Gesamt:"), str(total_beads)])

            bead_table = Table(bead_data, colWidths=[10 * mm, 15 * mm, 40 * mm, 55 * mm, 20 * mm])

            bead_style = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8b5cf6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (1, -1), "CENTER"),
                ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f4fc")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ]

            for row, stat in enumerate(bead_stats, 1):
                thread = stat["thread"]
                fill = colors.Color(
                    thread.color.r / 255,
                    thread.color.g / 255,
                    thread.color.b / 255,
                )
                bead_style.append(("BACKGROUND", (0, row), (0, row), fill))

            bead_table.setStyle(TableStyle(bead_style))
            elements.append(bead_table)

        return elements

    def _create_overview(self, pages_x: int, pages_y: int) -> list:
        """Erstellt die Übersichts-Seite."""
        from ..core.i18n import t
        from .export_common import terms_for

        elements = []

        total_pages = pages_x * pages_y

        unit_label = terms_for(self.pattern)["unit_plural"]
        elements.append(Paragraph(t("Seitenübersicht"), self._styles["Title1"]))
        elements.append(
            Paragraph(
                t(
                    "{total} Musterseiten · {px} Spalten × {py} Zeilen · je {w}×{h} {unit} · {fmt}"
                ).format(
                    total=total_pages,
                    px=pages_x,
                    py=pages_y,
                    w=self.STITCHES_PER_PAGE_X,
                    h=self.STITCHES_PER_PAGE_Y,
                    unit=unit_label,
                    fmt=self._page_format_name,
                ),
                self._styles["CenterText"],
            )
        )

        elements.append(Spacer(1, 10 * mm))

        # Mini-Vorschau mit Seitengrenzen (dynamisch)
        max_preview_w = self._available_width * 0.6
        max_preview_h = self._available_height * 0.35
        preview_width = max_preview_w
        preview_height = preview_width * self.pattern.height / self.pattern.width
        if preview_height > max_preview_h:
            preview_height = max_preview_h
            preview_width = preview_height * self.pattern.width / self.pattern.height

        preview = self._create_preview_drawing(preview_width, preview_height)
        if preview:
            # Seitengrenzen hinzufügen
            cell_w = preview_width / self.pattern.width
            cell_h = preview_height / self.pattern.height

            for sx in range(1, pages_x):
                line_x = sx * self.STITCHES_PER_PAGE_X * cell_w
                preview.add(
                    Line(
                        line_x, 0, line_x, preview_height, strokeColor=colors.white, strokeWidth=1.5
                    )
                )

            for sy in range(1, pages_y):
                line_y = preview_height - sy * self.STITCHES_PER_PAGE_Y * cell_h
                preview.add(
                    Line(
                        0, line_y, preview_width, line_y, strokeColor=colors.white, strokeWidth=1.5
                    )
                )

            elements.append(preview)

        elements.append(Spacer(1, 10 * mm))

        # Seitentabelle
        page_data = []
        page_nr = 1

        for sy in range(pages_y):
            row = []
            for sx in range(pages_x):
                range_x1 = sx * self.STITCHES_PER_PAGE_X + 1
                range_x2 = min((sx + 1) * self.STITCHES_PER_PAGE_X, self.pattern.width)
                range_y1 = sy * self.STITCHES_PER_PAGE_Y + 1
                range_y2 = min((sy + 1) * self.STITCHES_PER_PAGE_Y, self.pattern.height)

                cell_text = t(
                    "Seite {page_nr}\nX: {range_x1}-{range_x2}\nY: {range_y1}-{range_y2}"
                ).format(
                    page_nr=page_nr,
                    range_x1=range_x1,
                    range_x2=range_x2,
                    range_y1=range_y1,
                    range_y2=range_y2,
                )
                row.append(cell_text)
                page_nr += 1
            page_data.append(row)

        cell_width = min(35 * mm, self._available_width * 0.9 / pages_x)
        table = Table(page_data, colWidths=[cell_width] * pages_x)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f4ff")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#333333")),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#667eea")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        elements.append(table)

        return elements

    def _create_pattern_page(
        self, page_num: int, pages_x: int, pages_y: int, total_pages: int, title: str, date: str
    ) -> list:
        """Erstellt eine einzelne Musterseite mit integriertem Stickpfad."""
        from ..core.i18n import t

        elements = []

        page_x = page_num % pages_x
        page_y = page_num // pages_x

        overlap = getattr(self, "page_overlap_stitches", 0) or 0
        start_x = page_x * self.STITCHES_PER_PAGE_X
        start_y = page_y * self.STITCHES_PER_PAGE_Y
        core_end_x = start_x + self.STITCHES_PER_PAGE_X - 1
        core_end_y = start_y + self.STITCHES_PER_PAGE_Y - 1
        end_x = min(core_end_x + overlap, self.pattern.width - 1)
        end_y = min(core_end_y + overlap, self.pattern.height - 1)

        # Nachbarseiten für Page-Marker
        neighbors = []
        if page_x > 0:
            neighbors.append(t("&larr; S. {n}").format(n=page_num))
        if page_x < pages_x - 1:
            neighbors.append(t("S. {n} &rarr;").format(n=page_num + 2))
        if page_y > 0:
            neighbors.append(t("&uarr; S. {n}").format(n=page_num + 1 - pages_x))
        if page_y < pages_y - 1:
            neighbors.append(t("&darr; S. {n}").format(n=page_num + 1 + pages_x))
        neighbors_str = "  ".join(neighbors)

        # Header
        elements.append(
            Paragraph(
                t(
                    "<b>Seite {page} von {total}</b>  |  Spalten {sx}-{ex}  ·  Zeilen {sy}-{ey}"
                ).format(
                    page=page_num + 1,
                    total=total_pages,
                    sx=start_x + 1,
                    ex=end_x + 1,
                    sy=start_y + 1,
                    ey=end_y + 1,
                )
                + (
                    f"  |  <font size='8' color='#888'>{neighbors_str}</font>"
                    if neighbors_str
                    else ""
                ),
                self._styles["CenterText"],
            )
        )

        elements.append(Spacer(1, 3 * mm))

        # Pfade für diese Seite holen (wenn aktiviert)
        page_paths = []
        if self._include_path_preview and self._optimization_result:
            page_paths = self._get_page_color_paths(start_x, start_y, end_x, end_y)

        # Muster als Drawing mit integrierten Pfadlinien erstellen
        pattern_drawing = self._create_pattern_drawing_with_paths(
            start_x, start_y, end_x, end_y, page_paths
        )
        elements.append(pattern_drawing)

        # Mini-Legende
        elements.append(Spacer(1, 3 * mm))

        page_colors = self._count_page_colors(start_x, start_y, end_x, end_y)
        if page_colors:
            from .export_common import is_diamond_mode

            is_dp_pg = is_diamond_mode(self.pattern)
            legend_parts = []
            for stat in self._color_stats:
                if stat["index"] in page_colors:
                    thread = stat["thread"]
                    count = page_colors[stat["index"]]
                    code = thread.catalog_number or thread.name[:8]
                    if is_dp_pg:
                        # Farb-HTML-Box als Marker (reportlab unterstützt
                        # einfache <font>-Tags und <b>) — und kein Symbol,
                        # weil DP-Drills keine Symbol-Konvention haben.
                        # Die Box wird via Hex-Color als kleiner ASCII-Block ■ in der
                        # Thread-Farbe simuliert.
                        hex_color = thread.color.to_hex()
                        legend_parts.append(
                            f'<font color="{hex_color}">■</font> <b>{code}</b> ({count})'
                        )
                    else:
                        legend_parts.append(f"{stat['symbol']}={code} ({count})")

            legend_text = "  |  ".join(legend_parts[:12])  # Max 12 Farben anzeigen
            if len(page_colors) > 12:
                legend_text += t("  |  ... (+{n} weitere)").format(n=len(page_colors) - 12)

            elements.append(
                Paragraph(
                    f"<font size='7'><b>{t('Farben:')}</b> {legend_text}</font>",
                    self._styles["Normal"],
                )
            )

        # Pfad-Info wenn Pfade vorhanden — im DP-Modus uninteressant
        # (Drills folgen keiner Stickpfad-Logik, sondern werden zonen-weise
        # plaziert).
        from .export_common import is_diamond_mode

        if page_paths and not is_diamond_mode(self.pattern):
            total_stitches = sum(p.stitch_count for p in page_paths)
            total_jumps = sum(p.jump_count for p in page_paths)
            elements.append(
                Paragraph(
                    "<font size='7'>"
                    + t(
                        "<b>Stickpfad:</b> {stitches} Stiche  |  "
                        "{colors} Farben  |  {jumps} Sprünge  |  "
                        "<font color='#dd5555'>- - -</font> = Sprung"
                    ).format(
                        stitches=total_stitches,
                        colors=len(page_paths),
                        jumps=total_jumps,
                    )
                    + "</font>",
                    self._styles["Normal"],
                )
            )

        # Footer
        elements.append(Spacer(1, 2 * mm))
        elements.append(
            Paragraph(
                "<font size='7' color='#999999'>"
                + t("{title} · Seite {page}/{total} · {date}").format(
                    title=title, page=page_num + 1, total=total_pages, date=date
                )
                + "</font>",
                self._styles["CenterText"],
            )
        )

        return elements
