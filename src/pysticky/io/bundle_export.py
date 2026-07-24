"""
Bundle-Export: ZIP mit allen relevanten Dateien zum Teilen oder Backup.

Das Bundle enthält:
- `<name>.pxs`             — Original-Muster
- `<name>.html`            — HTML-Anleitung
- `<name>.png`             — Bild-Export
- `<name>.pdf`             — PDF (nur wenn reportlab installiert)
- `garnliste.csv`          — Maschinenlesbare Garn-Bedarfsliste
- `original/<basename>`    — Originalbild, falls Pattern aus einem Bild importiert
- `README.txt`             — kurze Beschreibung des Bundle-Inhalts

Synchron — der MainWindow-Handler ruft das in einem Worker auf.
"""

from __future__ import annotations

import csv
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core import Pattern


def _safe_basename(pattern: "Pattern") -> str:
    """Datei-sicherer Name für das Bundle (ohne Leer-/Sonderzeichen)."""
    import re

    name = pattern.name or "muster"
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_")
    return cleaned or "muster"


def _write_thread_csv(pattern: "Pattern", path: Path) -> None:
    """Schreibt eine kompakte Garn-/Drill-Bedarfsliste als CSV (kein UI-Code).

    Im Diamond-Painting-Modus ergibt eine Garn-Straehnen/Skein-Schaetzung
    keinen Sinn (Drills werden nicht in Straehnen abgezaehlt) -- der
    Statistik-Dialog blendet den entsprechenden Tab in DP deshalb komplett
    aus (siehe dp-stitch-parity-2026-07-18.md). Diese CSV war der einzige
    Export-Pfad, der das nicht nachvollzogen hatte: Sie schrieb fuer JEDES
    Pattern unveraendert "Stiche"/"Strange (~)" in den Header und rechnete
    eine Skein-Spalte aus, auch fuer DP-Muster.
    """
    import math

    from ..core.constants import DEFAULT_STITCHES_PER_SKEIN, STITCHES_PER_SKEIN
    from .export_common import is_diamond_mode

    is_dp = is_diamond_mode(pattern)
    stitches_per_skein = STITCHES_PER_SKEIN.get(pattern.fabric_count, DEFAULT_STITCHES_PER_SKEIN)

    # "utf-8-sig" statt "utf-8": schreibt eine UTF-8-BOM an den Dateianfang.
    # Ohne BOM interpretiert Excel eine per Doppelklick geoeffnete CSV ueber
    # die System-Codepage (auf deutschem Windows meist cp1252) statt UTF-8 --
    # Umlaute im Garnnamen (z.B. "Türkisblau") werden dann als Mojibake
    # ("TÃ¼rkisblau") angezeigt, obwohl die Datei selbst korrekt kodiert ist.
    # csv.reader/Python liest beide Varianten unveraendert korrekt, das BOM
    # stoert dort nicht (siehe test_bundle_csv_excel_bom_for_umlauts).
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        if is_dp:
            writer.writerow(["Symbol", "Hersteller", "Nr.", "Name", "Hex", "Drills"])
        else:
            writer.writerow(["Symbol", "Hersteller", "Nr.", "Name", "Hex", "Stiche", "Strange (~)"])
        for entry in pattern.color_entries:
            if entry.skip_stitching:
                continue
            t = entry.thread
            row = [
                entry.symbol,
                t.manufacturer or "",
                t.catalog_number or "",
                t.name,
                t.color.to_hex(),
                entry.stitch_count,
            ]
            if not is_dp:
                skeins = (
                    math.ceil(entry.stitch_count / stitches_per_skein) if entry.stitch_count else 0
                )
                row.append(skeins)
            writer.writerow(row)


def _write_readme(pattern: "Pattern", path: Path, contents: list[str]) -> None:
    """Erzeugt ein README mit der Liste enthaltener Dateien."""
    from .export_common import fabric_label_for, is_diamond_mode, terms_for

    terms = terms_for(pattern)
    size_line = terms["size_unit_template"].format(w=pattern.width, h=pattern.height)
    # Stoffzaehlung ("14 ct") ist im DP-Modus bedeutungslos (kein Aida-Stoff) --
    # dort stattdessen das Drill-Raster (z.B. "2.5 mm Square") ausgeben,
    # analog zu fabric_label_for()'s Nutzung in HTML-/PDF-Export.
    fabric_line = (
        f"{terms['fabric_label']}: {fabric_label_for(pattern)}"
        if is_diamond_mode(pattern)
        else f"Stoffzaehlung: {pattern.fabric_count} ct"
    )
    lines = [
        f"PySticky-Bundle: {pattern.name}",
        "=" * 60,
        f"Größe: {size_line}",
        fabric_line,
        f"Farben: {len(pattern.color_entries)}",
        "",
        "Enthaltene Dateien:",
    ]
    lines.extend(f"  - {name}" for name in contents)
    lines.append("")
    lines.append("Geöffnet werden kann das .pxs in PySticky.")
    path.write_text("\n".join(lines), encoding="utf-8")


def export_bundle(
    pattern: "Pattern",
    zip_path: Path | str,
    *,
    include_pdf: bool = True,
    pdf_page_format: str = "A4",
) -> dict:
    """Packt ein vollständiges Bundle als ZIP.

    Args:
        pattern: Das Muster.
        zip_path: Ziel-ZIP-Datei.
        include_pdf: Wenn True und reportlab vorhanden, PDF mit ins Bundle.
        pdf_page_format: Papierformat-Key für den PDF-Export (siehe
            PDFExporter.PAGE_FORMATS). Default A4.

    Returns:
        dict mit `zip_path`, `files` (Liste der Dateien im Bundle),
        `skipped` (Liste der Komponenten, die nicht erzeugt werden konnten).
    """
    from ..core import save_pattern
    from . import HTMLExporter, ImageExporter

    zip_path = Path(zip_path)
    base = _safe_basename(pattern)
    skipped: list[str] = []
    files_in_zip: list[str] = []

    with tempfile.TemporaryDirectory(prefix="pysticky_bundle_") as tmpdir:
        tmp = Path(tmpdir)

        # 1. .pxs
        pxs_path = tmp / f"{base}.pxs"
        save_pattern(pattern, pxs_path)
        files_in_zip.append(pxs_path.name)

        # 2. HTML
        html_path = tmp / f"{base}.html"
        try:
            HTMLExporter(pattern).export(html_path)
            files_in_zip.append(html_path.name)
        except Exception as exc:  # noqa: BLE001
            skipped.append(f"html ({exc})")

        # 3. PNG
        png_path = tmp / f"{base}.png"
        try:
            ImageExporter(pattern).export(
                png_path,
                cell_size=12,
                show_grid=True,
                show_symbols=False,
            )
            files_in_zip.append(png_path.name)
        except Exception as exc:  # noqa: BLE001
            skipped.append(f"png ({exc})")

        # 4. PDF — optional + nur wenn reportlab installiert
        if include_pdf:
            try:
                from . import PDFExporter, check_reportlab_available

                if check_reportlab_available():
                    pdf_path = tmp / f"{base}.pdf"
                    PDFExporter(pattern, page_format=pdf_page_format).export(pdf_path)
                    files_in_zip.append(pdf_path.name)
                else:
                    skipped.append("pdf (reportlab fehlt)")
            except Exception as exc:  # noqa: BLE001
                skipped.append(f"pdf ({exc})")

        # 5. Garnliste
        csv_path = tmp / "garnliste.csv"
        _write_thread_csv(pattern, csv_path)
        files_in_zip.append(csv_path.name)

        # 6. Originalbild — falls vorhanden. Wie die anderen optionalen
        # Bestandteile (HTML/PNG/PDF) fehlertolerant: ein Kopierfehler
        # (Berechtigungen, Platte voll, Datei gerade gesperrt) darf nicht
        # das gesamte Bundle verhindern, nur diesen einen Bestandteil
        # überspringen.
        source_dir_relative: str | None = None
        if pattern.source_image_path:
            src = Path(pattern.source_image_path)
            if src.exists():
                try:
                    src_dir = tmp / "original"
                    src_dir.mkdir()
                    dest = src_dir / src.name
                    shutil.copy2(src, dest)
                    source_dir_relative = f"original/{src.name}"
                    files_in_zip.append(source_dir_relative)
                except OSError as exc:
                    skipped.append(f"original ({exc})")
            else:
                skipped.append(f"original ({src.name} nicht gefunden)")

        # 7. README
        readme_path = tmp / "README.txt"
        _write_readme(pattern, readme_path, files_in_zip)
        files_in_zip.append(readme_path.name)

        # ZIP schreiben (deflated, default level) -- atomar wie
        # core/file_io.py::save_pattern(): erst in eine Temp-Datei NEBEN
        # dem Ziel, dann per os.replace() (atomar auf POSIX UND Windows,
        # anders als os.rename()) an die Zielposition verschieben. Ohne
        # das wuerde ein Crash/Abbruch waehrend des (bei mehreren
        # gebuendelten Dateien nicht ganz kurzen) ZIP-Schreibens ein
        # bereits vorhandenes Bundle an genau diesem Pfad (z.B. ein
        # erneuter Export/Teilen desselben Musters) durch eine
        # abgeschnittene/korrupte ZIP-Datei ersetzen.
        zip_temp_path = zip_path.with_name(zip_path.name + ".tmp")
        try:
            with zipfile.ZipFile(zip_temp_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for name in files_in_zip:
                    zf.write(tmp / name, arcname=name)
            os.replace(zip_temp_path, zip_path)
        except BaseException:
            try:
                zip_temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    return {
        "zip_path": str(zip_path),
        "files": files_in_zip,
        "skipped": skipped,
    }
