"""
OXS (Open Cross Stitch) Dateiformat-Import und -Export.

OXS ist ein XML-basiertes, offenes Austauschformat für Kreuzstich-Muster.
Es wird von Pattern Maker, MacStitch/WinStitch (Ursa Software), Stitch Fiddle
und anderen unterstützt und ist damit die de-facto-Brücke zwischen den
verschiedenen kommerziellen Tools.

Format (vereinfachte Struktur):

    <chart>
      <format>
        <FormatVersion value="1.0" />
      </format>
      <chart_info>
        <title value="..." />
        <author value="..." />
        <copyright value="..." />
        <chartwidth value="50" />
        <chartheight value="50" />
        <stitchesperinch value="14" />
        <stitchesperinch_y value="14" />
      </chart_info>
      <palette>
        <palette_item index="0" name="cloth" color="FFFFFF" />
        <palette_item index="1" number="310" name="DMC 310" symbol="X" color="000000" />
        ...
      </palette>
      <fullstitches>
        <stitch x="1" y="1" palindex="1" />
        ...
      </fullstitches>
      <halfstitches>
        <halfstitch x="2" y="2" palindex="1" direction="1" />  <!-- 1=TL_BR, 2=TR_BL -->
        ...
      </halfstitches>
      <quarterstitches>
        <quarterstitch x="3" y="3" palindex="1" position="TL" />  <!-- TL/TR/BL/BR -->
        ...
      </quarterstitches>
      <threequarterstitches>
        <threequarterstitch x="4" y="4" palindex="1" />
        ...
      </threequarterstitches>
      <backstitches>
        <backstitch x1="1" y1="1" x2="2" y2="1" palindex="1" />
        ...
      </backstitches>
      <ornaments_inc_knots_and_beads>
        <object x1="1.5" y1="1.5" palindex="1" objecttype="knot" />
        <object x1="2.5" y1="2.5" palindex="1" objecttype="bead" />
      </ornaments_inc_knots_and_beads>
    </chart>

Koordinaten-Konventionen:
- Vollstiche etc.:    OXS 1-indiziert, ganze Zahlen. pattern_x = oxs_x - 1
- Backstitches:       OXS in halben Stichen ab 1.0 (ganze Zahlen!) bei Ursa-Variante.
                      pattern_half_x = (oxs_x - 1) * 2
                      Eckpunkt (0,0) im Pattern -> OXS (1,1).
                      Mitte (1,1) im Pattern -> OXS (1.5,1.5).
- Knots/Beads:        OXS .5-Float-Koord (Zellmitte). pattern_x = int(oxs_x - 1.5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import parse as _safe_parse

from ...core.layer import NO_STITCH
from ...core.palette import get_palette_manager
from ...core.pattern import Pattern
from ...core.stitch import StitchType
from ...core.thread import Thread, ThreadColor


class OXSImportError(Exception):
    """Fehler beim Importieren einer OXS-Datei."""


class OXSExportError(Exception):
    """Fehler beim Exportieren einer OXS-Datei."""


# Quarter-Position-String -> StitchType-Code
_QUARTER_POS_TO_CODE = {
    "TL": StitchType.QUARTER_TL.value,
    "TR": StitchType.QUARTER_TR.value,
    "BL": StitchType.QUARTER_BL.value,
    "BR": StitchType.QUARTER_BR.value,
}
_CODE_TO_QUARTER_POS = {v: k for k, v in _QUARTER_POS_TO_CODE.items()}


@dataclass
class OXSImporter:
    """Liest eine .oxs-Datei und liefert ein Pattern."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def can_import(self, filepath: Path | str) -> bool:
        filepath = Path(filepath)
        if not filepath.exists() or filepath.suffix.lower() != ".oxs":
            return False
        try:
            # Probiere als XML zu parsen — minimaler Check.
            # _safe_parse (defusedxml) blockt XXE/Entity-Expansion.
            _safe_parse(filepath).getroot()
            return True
        except (ET.ParseError, OSError, DefusedXmlException):
            return False

    def import_file(self, filepath: Path | str) -> Pattern | None:
        filepath = Path(filepath)
        self.errors.clear()
        self.warnings.clear()

        if not filepath.exists():
            self.errors.append(f"Datei nicht gefunden: {filepath}")
            return None

        try:
            # _safe_parse (defusedxml): Schutz vor XXE / Billion-Laughs,
            # da OXS-Dateien aus fremder Quelle stammen können.
            tree = _safe_parse(filepath)
        except ET.ParseError as e:
            self.errors.append(f"XML-Parse-Fehler: {e}")
            return None
        except DefusedXmlException as e:
            self.errors.append(f"Unsicheres XML abgelehnt: {e}")
            return None
        except OSError as e:
            self.errors.append(f"Lese-Fehler: {e}")
            return None

        try:
            return self._parse_chart(tree.getroot(), filepath.stem)
        except OXSImportError as e:
            self.errors.append(str(e))
            return None

    def _parse_chart(self, root: ET.Element, default_name: str) -> Pattern:
        if root.tag != "chart":
            raise OXSImportError(f"Root-Element ist '{root.tag}', erwartet 'chart'")

        # chart_info
        info = root.find("chart_info")
        if info is None:
            info = ET.Element("chart_info")
        title = _attr_value(info, "title") or default_name
        author = _attr_value(info, "author") or ""
        copyright_ = _attr_value(info, "copyright") or ""
        width = _attr_int(info, "chartwidth", default=0)
        height = _attr_int(info, "chartheight", default=0)
        spi = _attr_int(info, "stitchesperinch", default=14)

        if width < 1 or height < 1:
            raise OXSImportError(f"Ungueltige Dimensionen: {width}x{height}")

        # Pattern aufsetzen
        pattern = Pattern(
            name=title,
            width=width,
            height=height,
            fabric_count=spi,
        )
        pattern.color_entries.clear()
        if author:
            pattern.metadata["author"] = author
        if copyright_:
            pattern.metadata["copyright"] = copyright_
        pattern.metadata["imported_from"] = "oxs"

        # Palette: OXS-palindex -> Pattern-color-index
        palindex_map: dict[int, int] = self._read_palette(root, pattern)

        # Stiche
        self._read_full_stitches(root, pattern, palindex_map)
        self._read_half_stitches(root, pattern, palindex_map)
        self._read_quarter_stitches(root, pattern, palindex_map)
        self._read_three_quarter_stitches(root, pattern, palindex_map)
        self._read_backstitches(root, pattern, palindex_map)
        self._read_ornaments(root, pattern, palindex_map)

        return pattern

    def _read_palette(
        self,
        root: ET.Element,
        pattern: Pattern,
    ) -> dict[int, int]:
        """Liest <palette> und liefert palindex->color_entries-Mapping."""
        palette_el = root.find("palette")
        if palette_el is None:
            raise OXSImportError("Keine <palette>-Section gefunden")

        # Thread-Lookup über alle bekannten Hersteller-Paletten, für
        # Matching "DMC 310" -> echter Thread aus der DMC-Palette.
        # Zusätzlich: merken welche Threads aus Bead-Paletten stammen.
        pm = get_palette_manager()
        pm.load_all()
        all_threads_by_key: dict[tuple[str, str], Thread] = {}
        bead_keys: set[tuple[str, str]] = set()
        diamond_keys: set[tuple[str, str]] = set()
        for palette_name in pm.available_palettes:
            palette = pm.get_palette(palette_name)
            if palette is None:
                continue
            for pal_thread in palette.threads:
                if pal_thread.manufacturer and pal_thread.catalog_number:
                    key = (
                        pal_thread.manufacturer.lower(),
                        pal_thread.catalog_number.lower(),
                    )
                    all_threads_by_key.setdefault(key, pal_thread)
                    if palette.is_beads:
                        bead_keys.add(key)
                    if palette.is_diamond:
                        diamond_keys.add(key)

        palindex_map: dict[int, int] = {}

        for item in palette_el.findall("palette_item"):
            idx_str = item.get("index", "")
            try:
                palindex = int(idx_str)
            except ValueError:
                self.warnings.append(f"Palette-Item ohne gueltigen Index: {idx_str}")
                continue

            number = item.get("number", "").strip()
            name = item.get("name", "").strip()
            symbol = item.get("symbol", "").strip()
            color_hex = item.get("color", "").strip()

            # index=0 ist per Konvention "cloth" — überspringen
            if palindex == 0 and (name.lower() in {"cloth", "fabric", ""} or number == ""):
                continue

            # Manufacturer und Catalog-Number aus name extrahieren, z.B. "DMC 310"
            manufacturer, catalog = _parse_manufacturer_catalog(name, number)

            # Falls in bekannter Palette: realen Thread verwenden, damit
            # Cross-Reference und Hersteller-Konvertierung greifen
            thread: Thread | None = None
            is_bead = False
            is_diamond = False
            if manufacturer and catalog:
                key = (manufacturer.lower(), catalog.lower())
                thread = all_threads_by_key.get(key)
                is_bead = key in bead_keys
                is_diamond = key in diamond_keys

            if thread is None:
                # Fallback: Thread aus OXS-Daten konstruieren
                try:
                    color = ThreadColor.from_hex(color_hex or "#000000")
                except (ValueError, IndexError):
                    self.warnings.append(
                        f"Ungueltige Farbe '{color_hex}' für Palette-Item {palindex}"
                    )
                    color = ThreadColor(0, 0, 0)
                thread = Thread(
                    name=name or f"Color {palindex}",
                    color=color,
                    manufacturer=manufacturer,
                    catalog_number=catalog,
                )
                # Heuristik: Manufacturer-Name enthält "Bead" oder "Diamond"
                if manufacturer:
                    mfr_lower = manufacturer.lower()
                    if "bead" in mfr_lower:
                        is_bead = True
                    elif "diamond" in mfr_lower:
                        is_diamond = True

            # Blend-Komponenten aus Custom-Attribute rekonstruieren
            blend_csv = item.get("blend_components", "")
            ratios_csv = item.get("blend_ratios", "")
            if blend_csv:
                components: list[Thread] = []
                for piece in blend_csv.split(";"):
                    parts = piece.split("|")
                    if len(parts) >= 4:
                        comp_mfr, comp_num, comp_hex, comp_name = parts[:4]
                        try:
                            comp_color = ThreadColor.from_hex(comp_hex)
                        except (ValueError, IndexError):
                            continue
                        components.append(
                            Thread(
                                name=comp_name,
                                color=comp_color,
                                manufacturer=comp_mfr or None,
                                catalog_number=comp_num or None,
                            )
                        )
                if len(components) >= 2:
                    thread.blend_components = components
                    if ratios_csv:
                        try:
                            thread.strand_ratios = [
                                int(r) for r in ratios_csv.split(",") if r.strip()
                            ]
                        except ValueError:
                            thread.strand_ratios = [1] * len(components)
                    else:
                        thread.strand_ratios = [1] * len(components)

            # In Pattern einfügen
            pattern_idx = pattern.add_color(thread, is_bead=is_bead, is_diamond=is_diamond)
            # Symbol übernehmen wenn aus OXS gesetzt
            if symbol:
                pattern.set_symbol(pattern_idx, symbol)
            palindex_map[palindex] = pattern_idx

        return palindex_map

    def _read_full_stitches(
        self,
        root: ET.Element,
        pattern: Pattern,
        palindex_map: dict[int, int],
    ) -> None:
        section = root.find("fullstitches")
        if section is None:
            return
        for el in section.findall("stitch"):
            x, y, idx = _parse_stitch_xy_palindex(el)
            if x is None or y is None or idx is None:
                continue
            color_idx = palindex_map.get(idx)
            if color_idx is None:
                continue
            self._place_stitch(pattern, x - 1, y - 1, color_idx, StitchType.FULL.value)

    def _read_half_stitches(
        self,
        root: ET.Element,
        pattern: Pattern,
        palindex_map: dict[int, int],
    ) -> None:
        section = root.find("halfstitches")
        if section is None:
            return
        for el in section.findall("halfstitch"):
            x, y, idx = _parse_stitch_xy_palindex(el)
            if x is None or y is None or idx is None:
                continue
            color_idx = palindex_map.get(idx)
            if color_idx is None:
                continue
            direction = el.get("direction", "1")
            stitch_code = (
                StitchType.HALF_TL_BR.value if direction == "1" else StitchType.HALF_TR_BL.value
            )
            self._place_stitch(pattern, x - 1, y - 1, color_idx, stitch_code)

    def _read_quarter_stitches(
        self,
        root: ET.Element,
        pattern: Pattern,
        palindex_map: dict[int, int],
    ) -> None:
        section = root.find("quarterstitches")
        if section is None:
            return
        for el in section.findall("quarterstitch"):
            x, y, idx = _parse_stitch_xy_palindex(el)
            if x is None or y is None or idx is None:
                continue
            color_idx = palindex_map.get(idx)
            if color_idx is None:
                continue
            position = el.get("position", "TL").upper()
            stitch_code = _QUARTER_POS_TO_CODE.get(position, StitchType.QUARTER_TL.value)
            self._place_stitch(pattern, x - 1, y - 1, color_idx, stitch_code)

    def _read_three_quarter_stitches(
        self,
        root: ET.Element,
        pattern: Pattern,
        palindex_map: dict[int, int],
    ) -> None:
        section = root.find("threequarterstitches")
        if section is None:
            return
        for el in section.findall("threequarterstitch"):
            x, y, idx = _parse_stitch_xy_palindex(el)
            if x is None or y is None or idx is None:
                continue
            color_idx = palindex_map.get(idx)
            if color_idx is None:
                continue
            self._place_stitch(pattern, x - 1, y - 1, color_idx, StitchType.THREE_QUARTER.value)

    def _read_backstitches(
        self,
        root: ET.Element,
        pattern: Pattern,
        palindex_map: dict[int, int],
    ) -> None:
        section = root.find("backstitches")
        if section is None:
            return
        for el in section.findall("backstitch"):
            try:
                x1 = float(el.get("x1", ""))
                y1 = float(el.get("y1", ""))
                x2 = float(el.get("x2", ""))
                y2 = float(el.get("y2", ""))
                palindex = int(el.get("palindex", ""))
            except (ValueError, TypeError):
                continue
            color_idx = palindex_map.get(palindex)
            if color_idx is None:
                continue
            # OXS-Koord 1-basiert (Ecke der ersten Zelle = 1,1; Mitte = 1.5,1.5)
            # Pattern-Half-Stitch-Koord (Ecke = 0,0; Mitte = 1,1)
            hx1 = int(round((x1 - 1) * 2))
            hy1 = int(round((y1 - 1) * 2))
            hx2 = int(round((x2 - 1) * 2))
            hy2 = int(round((y2 - 1) * 2))
            pattern.add_backstitch(hx1, hy1, hx2, hy2, color_idx)

    def _read_ornaments(
        self,
        root: ET.Element,
        pattern: Pattern,
        palindex_map: dict[int, int],
    ) -> None:
        # OXS verwendet hier "ornaments_inc_knots_and_beads" (kanonisch)
        # oder "ornaments" als Aliasing — beide akzeptieren.
        section = root.find("ornaments_inc_knots_and_beads")
        if section is None:
            section = root.find("ornaments")
        if section is None:
            return

        for el in section.findall("object"):
            try:
                x1 = float(el.get("x1", ""))
                y1 = float(el.get("y1", ""))
                palindex = int(el.get("palindex", ""))
            except (ValueError, TypeError):
                continue
            color_idx = palindex_map.get(palindex)
            if color_idx is None:
                continue

            objtype = el.get("objecttype", "knot").lower()
            if objtype == "knot":
                stitch_code = StitchType.FRENCH_KNOT.value
            elif objtype == "bead":
                stitch_code = StitchType.BEAD.value
            else:
                self.warnings.append(f"Unbekannter Ornament-Typ: {objtype}")
                continue

            # OXS: x=1.5 für Mitte der ersten Zelle. Pattern: x=0 für erste Zelle.
            px = int(x1 - 1)
            py = int(y1 - 1)
            self._place_stitch(pattern, px, py, color_idx, stitch_code)

    def _place_stitch(
        self,
        pattern: Pattern,
        x: int,
        y: int,
        color_idx: int,
        stitch_type: int,
    ) -> None:
        """Setzt einen Stich in Pattern-Koord (0-basiert), mit Bounds-Check."""
        if 0 <= x < pattern.width and 0 <= y < pattern.height:
            pattern.set_stitch(x, y, color_idx, stitch_type=stitch_type)


@dataclass
class OXSExporter:
    """Schreibt ein Pattern als .oxs-Datei."""

    def export_file(
        self,
        pattern: Pattern,
        filepath: Path | str,
        author: str | None = None,
        copyright_: str | None = None,
    ) -> None:
        filepath = Path(filepath)
        root = self._build_tree(pattern, author=author, copyright_=copyright_)
        tree = ET.ElementTree(root)
        # ET.indent existiert seit Python 3.9 — pretty-print
        ET.indent(tree, space="  ")
        try:
            tree.write(filepath, encoding="utf-8", xml_declaration=True)
        except OSError as e:
            raise OXSExportError(f"Konnte OXS-Datei nicht schreiben: {e}")

    def _build_tree(
        self,
        pattern: Pattern,
        author: str | None = None,
        copyright_: str | None = None,
    ) -> ET.Element:
        chart = ET.Element("chart")

        # <format>
        fmt = ET.SubElement(chart, "format")
        ET.SubElement(
            fmt,
            "FormatVersion",
            attrib={"value": "1.0"},
        )
        fmt.set(
            "comments_about_this_chart_format",
            "OXS — Open Cross Stitch XML",
        )

        # <chart_info>
        info = ET.SubElement(chart, "chart_info")
        _add_value_child(info, "title", pattern.name or "")
        _add_value_child(
            info,
            "author",
            author if author is not None else pattern.metadata.get("author", ""),
        )
        _add_value_child(
            info,
            "copyright",
            copyright_ if copyright_ is not None else pattern.metadata.get("copyright", ""),
        )
        _add_value_child(info, "chartwidth", str(pattern.width))
        _add_value_child(info, "chartheight", str(pattern.height))
        _add_value_child(info, "stitchesperinch", str(pattern.fabric_count))
        _add_value_child(info, "stitchesperinch_y", str(pattern.fabric_count))

        # <palette>
        palette_el = ET.SubElement(chart, "palette")
        # Index 0 ist Konvention: cloth
        ET.SubElement(
            palette_el,
            "palette_item",
            attrib={
                "index": "0",
                "number": "cloth",
                "name": "cloth",
                "symbol": "",
                "color": "FFFFFF",
            },
        )
        for i, entry in enumerate(pattern.color_entries):
            thread = entry.thread
            number = (thread.catalog_number or "").strip()
            mfr = (thread.manufacturer or "").strip()
            display_name = thread.name or f"Color {i + 1}"
            if mfr and number:
                # Sauberer Name, damit der Reader es zurück-mappen kann
                display_name = f"{mfr} {number} - {thread.name}"
            attrib = {
                "index": str(i + 1),
                "number": number or display_name,
                "name": display_name,
                "symbol": entry.symbol or "",
                "color": thread.color.to_hex().lstrip("#"),
            }
            # Tweed-Blend: Komponenten als Custom-Attribute mitgeben.
            # OXS-Standard kennt das nicht, aber Custom-Attribute werden
            # von anderen Tools ignoriert — kein Datenverlust auf der
            # Empfängerseite, und wir können den Blend bei Re-Import
            # rekonstruieren.
            if thread.is_blend:
                attrib["blend_components"] = ";".join(
                    f"{(c.manufacturer or '').strip()}|{(c.catalog_number or '').strip()}|{c.color.to_hex().lstrip('#')}|{c.name}"
                    for c in (thread.blend_components or [])
                )
                attrib["blend_ratios"] = ",".join(str(r) for r in (thread.strand_ratios or []))
            ET.SubElement(palette_el, "palette_item", attrib=attrib)

        # Stiche aus allen sichtbaren Layern zusammenführen — composite
        fullstitches = ET.SubElement(chart, "fullstitches")
        halfstitches = ET.SubElement(chart, "halfstitches")
        quarterstitches = ET.SubElement(chart, "quarterstitches")
        threequarterstitches = ET.SubElement(chart, "threequarterstitches")
        backstitches = ET.SubElement(chart, "backstitches")
        ornaments = ET.SubElement(chart, "ornaments_inc_knots_and_beads")

        # Composite-Grid berechnen (sichtbare Layer von unten nach oben)
        composite = pattern.layer_stack.get_composite_grid()
        composite_types = pattern.layer_stack.get_composite_stitch_type_grid()

        for y in range(pattern.height):
            for x in range(pattern.width):
                color_idx = int(composite[y, x])
                if color_idx == NO_STITCH:
                    continue
                stitch_code = int(composite_types[y, x])
                palindex = color_idx + 1  # +1 wegen cloth-entry

                if stitch_code == StitchType.FULL.value:
                    ET.SubElement(
                        fullstitches,
                        "stitch",
                        attrib={
                            "x": str(x + 1),
                            "y": str(y + 1),
                            "palindex": str(palindex),
                        },
                    )
                elif stitch_code in (
                    StitchType.HALF_TL_BR.value,
                    StitchType.HALF_TR_BL.value,
                ):
                    direction = "1" if stitch_code == StitchType.HALF_TL_BR.value else "2"
                    ET.SubElement(
                        halfstitches,
                        "halfstitch",
                        attrib={
                            "x": str(x + 1),
                            "y": str(y + 1),
                            "palindex": str(palindex),
                            "direction": direction,
                        },
                    )
                elif stitch_code in _CODE_TO_QUARTER_POS:
                    ET.SubElement(
                        quarterstitches,
                        "quarterstitch",
                        attrib={
                            "x": str(x + 1),
                            "y": str(y + 1),
                            "palindex": str(palindex),
                            "position": _CODE_TO_QUARTER_POS[stitch_code],
                        },
                    )
                elif stitch_code == StitchType.THREE_QUARTER.value:
                    ET.SubElement(
                        threequarterstitches,
                        "threequarterstitch",
                        attrib={
                            "x": str(x + 1),
                            "y": str(y + 1),
                            "palindex": str(palindex),
                        },
                    )
                elif stitch_code == StitchType.FRENCH_KNOT.value:
                    ET.SubElement(
                        ornaments,
                        "object",
                        attrib={
                            "x1": f"{x + 1.5:.1f}",
                            "y1": f"{y + 1.5:.1f}",
                            "palindex": str(palindex),
                            "objecttype": "knot",
                        },
                    )
                elif stitch_code == StitchType.BEAD.value:
                    ET.SubElement(
                        ornaments,
                        "object",
                        attrib={
                            "x1": f"{x + 1.5:.1f}",
                            "y1": f"{y + 1.5:.1f}",
                            "palindex": str(palindex),
                            "objecttype": "bead",
                        },
                    )
                else:
                    # Unbekannter Code -> als Vollstich fallback
                    ET.SubElement(
                        fullstitches,
                        "stitch",
                        attrib={
                            "x": str(x + 1),
                            "y": str(y + 1),
                            "palindex": str(palindex),
                        },
                    )

        # Backstitches
        for bs in pattern.backstitch_manager.backstitches:
            # Pattern-Halb-Stich-Koord -> OXS (1-basiert)
            x1 = bs.x1 / 2.0 + 1.0
            y1 = bs.y1 / 2.0 + 1.0
            x2 = bs.x2 / 2.0 + 1.0
            y2 = bs.y2 / 2.0 + 1.0
            ET.SubElement(
                backstitches,
                "backstitch",
                attrib={
                    "x1": _fmt_coord(x1),
                    "y1": _fmt_coord(y1),
                    "x2": _fmt_coord(x2),
                    "y2": _fmt_coord(y2),
                    "palindex": str(bs.color_index + 1),
                },
            )

        return chart


# ---------- Helpers ----------


def _attr_value(parent: ET.Element, tag: str) -> str | None:
    """Liefert child.get('value') für das erste <tag>-Child, oder None."""
    el = parent.find(tag)
    if el is None:
        return None
    return el.get("value")


def _attr_int(parent: ET.Element, tag: str, default: int = 0) -> int:
    """Wie _attr_value, aber int mit default bei Fehler."""
    val = _attr_value(parent, tag)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _parse_stitch_xy_palindex(
    el: ET.Element,
) -> tuple[int | None, int | None, int | None]:
    """Liest x, y, palindex aus einem <stitch>-ähnlichen Element."""
    try:
        x = int(el.get("x", ""))
        y = int(el.get("y", ""))
        palindex = int(el.get("palindex", ""))
        return x, y, palindex
    except (ValueError, TypeError):
        return None, None, None


def _parse_manufacturer_catalog(
    name: str,
    number: str,
) -> tuple[str | None, str | None]:
    """
    Versucht aus name+number Hersteller und Katalog-Nummer zu extrahieren.

    Beispiele:
        ("DMC 310 - Black", "310") -> ("DMC", "310")
        ("Anchor 403", "")          -> ("Anchor", "403")
        ("310", "310")              -> (None, "310")
        ("cloth", "cloth")          -> (None, None)
    """
    if number and number.lower() in {"cloth", "fabric", ""}:
        return None, None

    if name and number:
        # Suche Hersteller-Präfix in name
        lower = name.lower()
        for mfr in _KNOWN_MANUFACTURERS:
            if lower.startswith(mfr.lower()):
                return mfr, number

    # Wenn name selber im Format "Hersteller NUMMER ..." ist
    parts = (name or "").split(None, 2)
    if len(parts) >= 2 and parts[0] in _KNOWN_MANUFACTURERS:
        return parts[0], parts[1]

    if number:
        return None, number

    return None, None


def _add_value_child(parent: ET.Element, tag: str, value: str) -> ET.Element:
    """Fügt <tag value="..."/> an parent an."""
    return ET.SubElement(parent, tag, attrib={"value": value})


def _fmt_coord(v: float) -> str:
    """Formatiert eine Koord-Float für OXS — int wenn ganz, sonst .1f."""
    if abs(v - round(v)) < 1e-6:
        return str(int(round(v)))
    return f"{v:.1f}"


_KNOWN_MANUFACTURERS = [
    # Mehrwort-Präfixe zuerst, damit startswith-Match greift, BEVOR
    # ein kürzeres Präfix wie "Mill" das verschluckt.
    "Mill Hill Beads",
    "Mill Hill",
    "Weeks Dye Works",
    "Classic Colorworks",
    "Gentle Art Sampler Threads",
    "Riolis Gamma",
    "DMC Diamond Painting",
    "DMC",
    "Anchor",
    "Madeira",
    "Cosmo",
    "Olympus",
    "Weeks",
    "Valdani",
    "Venus",
    "Finca",
    "Sullivans",
    "Riolis",
    "Gamma",
    "Classic",
    "Gentle",
    "Toho",
    "Miyuki",
]


def import_oxs(
    filepath: Path | str,
) -> tuple[Pattern | None, list[str], list[str]]:
    """Convenience: liest OXS, liefert (Pattern, Fehler, Warnungen)."""
    importer = OXSImporter()
    pattern = importer.import_file(filepath)
    return pattern, importer.errors, importer.warnings


def export_oxs(
    pattern: Pattern,
    filepath: Path | str,
    author: str | None = None,
    copyright_: str | None = None,
) -> None:
    """Convenience: schreibt Pattern als OXS-Datei."""
    exporter = OXSExporter()
    exporter.export_file(
        pattern,
        filepath,
        author=author,
        copyright_=copyright_,
    )
