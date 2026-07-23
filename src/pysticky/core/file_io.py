"""
Datei-I/O für PySticky Muster.

Speichert und lädt Muster im .pxs Format (JSON-basiert).

Das .pxs-Format ist ein offenes, menschenlesbares Format:
    - JSON-basiert für einfache Inspektion und Debugging
    - Kompakte Stich-Speicherung als [x, y, color_index] Listen
    - Versionierung für Vorwärtskompatibilität
    - Unterstützung für Layer, Backstitches und Metadaten

Format-Versionen:
    - 1.0: Initiales Format (Stiche, Farben, Layer)
    - 1.1: Backstitch-Unterstützung hinzugefügt
    - 1.2: Fortschritts-Tracking (completed_stitches pro Layer)
    - 1.3: Stichtypen pro Layer (stitch_types)
    - 1.4: Layer-Notizen (note); Pattern-Metadaten total_stitch_seconds
           und last_session_start für Sticken-Modus-Sessions
    - 1.5: Pattern.mode ("stitch"/"diamond"); Diamond-Stitch-Type (11)

Example:
    >>> from pysticky.core import save_pattern, load_pattern, Pattern
    >>> pattern = Pattern(name="Mein Muster", width=100, height=100)
    >>> save_pattern(pattern, "muster.pxs")
    >>> loaded = load_pattern("muster.pxs")
"""

import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .backstitch_manager import Backstitch
from .constants import DEFAULT_FABRIC_COUNT
from .layer import NO_STITCH, Layer, LayerStack
from .pattern import ColorEntry, Pattern
from .thread import Thread

# Dateiformat-Version
FORMAT_VERSION = "1.5"
"""Aktuelle Version des .pxs Dateiformats."""


def save_pattern(pattern: Pattern, filepath: Path | str) -> None:
    """
    Speichert ein Muster als .pxs Datei.

    Das Muster wird als JSON mit 2-Space Einrückung gespeichert.
    Enthält einen Zeitstempel des Speichervorgangs.

    Args:
        pattern: Das zu speichernde Muster
        filepath: Zielpfad (mit oder ohne .pxs Endung)

    Raises:
        OSError: Bei Schreibfehlern (Berechtigungen, Speicherplatz, etc.)

    Example:
        >>> save_pattern(pattern, "mein_muster.pxs")
        >>> save_pattern(pattern, Path("ordner/muster.pxs"))
    """
    filepath = Path(filepath)

    data = {
        "format": "pysticky",
        "version": FORMAT_VERSION,
        "saved_at": datetime.now().isoformat(),
        "pattern": _pattern_to_dict(pattern),
    }

    # Atomar schreiben: erst in eine Temp-Datei, dann per os.replace() (auf
    # POSIX UND Windows atomar, anders als os.rename()) an die Zielposition
    # verschieben. Ohne das wuerde ein Crash/Stromausfall mitten in
    # json.dump() die eigentliche Musterdatei truncated/korrupt
    # zuruecklassen -- Autosave (autosave_handlers.py) hat dieses Risiko
    # schon lange vermieden, der manuelle Speichern/Speichern-unter-Pfad
    # (der weitaus meistgenutzte) bislang nicht.
    temp_path = filepath.with_name(filepath.name + ".tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, filepath)
    except BaseException:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def load_pattern(filepath: Path | str) -> Pattern:
    """
    Lädt ein Muster aus einer .pxs Datei.

    Unterstützt alle Format-Versionen mit Vorwärtskompatibilität.
    Fehlende Felder werden mit Standardwerten gefüllt.

    Args:
        filepath: Pfad zur .pxs Datei

    Returns:
        Das geladene Pattern-Objekt

    Raises:
        FileNotFoundError: Wenn die Datei nicht existiert
        ValueError: Bei ungültigem Dateiformat oder beschädigter Struktur
            (fängt auch ungültige JSON-Syntax ab und wirft sie als
            ValueError weiter, statt json.JSONDecodeError nach aussen
            durchzulassen)

    Example:
        >>> pattern = load_pattern("mein_muster.pxs")
        >>> print(pattern.name, pattern.width, pattern.height)
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Fehlerhafte Datei-Syntax: {e}")

    # json.load() akzeptiert jedes gueltige JSON-Dokument als Top-Level-Wert,
    # nicht nur Objekte -- eine versehentlich umbenannte/vertauschte Datei
    # (z.B. eine JSON-Liste oder ein einzelner String/Zahl) laedt also
    # klaglos durch, und das folgende `data.get(...)` wuerde mit einem
    # rohen AttributeError crashen (list/str/int/None haben kein .get).
    # Das ist besonders beim Autosave-Recovery-Pfad relevant (_check_
    # autosave_recovery), der genau diesen Fall (fremde Datei liegt unter
    # dem erwarteten Autosave-Namen) abfangen koennen muss.
    if not isinstance(data, dict):
        raise ValueError(
            f"Ungültiges Dateiformat: JSON-Objekt erwartet, gefunden {type(data).__name__}"
        )

    if data.get("format") != "pysticky":
        raise ValueError(
            f"Ungültiges Dateiformat: erwartet 'pysticky', "
            f"gefunden '{data.get('format', 'unbekannt')}'"
        )

    if "pattern" not in data:
        raise ValueError("Datei enthält keine Muster-Daten")

    pattern_data = data["pattern"]
    if not isinstance(pattern_data, dict):
        raise ValueError(
            f"Ungültige Musterdaten: Objekt erwartet, gefunden {type(pattern_data).__name__}"
        )

    return _dict_to_pattern(pattern_data)


def _pattern_to_dict(pattern: Pattern) -> dict[str, Any]:
    """
    Konvertiert ein Pattern zu einem serialisierbaren Dictionary.

    Interne Funktion für save_pattern().

    Args:
        pattern: Das zu konvertierende Pattern

    Returns:
        Dictionary mit allen Pattern-Daten
    """
    return {
        "name": pattern.name,
        "width": pattern.width,
        "height": pattern.height,
        "fabric_count": pattern.fabric_count,
        "metadata": pattern.metadata,
        "colors": [_color_entry_to_dict(c) for c in pattern.color_entries],
        "layers": [_layer_to_dict(l) for l in pattern.layer_stack],
        "active_layer": pattern.layer_stack.active_index,
        # Rückstiche (seit v1.1)
        "backstitches": [_backstitch_to_dict(bs) for bs in pattern.backstitches],
        # Quell-Infos für Palettenwechsel
        "source_image_path": pattern.source_image_path,
        "source_image_crop": list(pattern.source_image_crop),
        "source_palette_name": pattern.source_palette_name,
        # Pattern-Modus (seit v1.5): "stitch" oder "diamond"
        "mode": pattern.mode,
    }


def _dict_to_pattern(data: dict[str, Any]) -> Pattern:
    """
    Konvertiert ein Dictionary zurück zu einem Pattern-Objekt.

    Interne Funktion für load_pattern().
    Verwendet Standardwerte für fehlende Felder (Vorwärtskompatibilität).

    Args:
        data: Dictionary aus der JSON-Datei

    Returns:
        Rekonstruiertes Pattern-Objekt

    Raises:
        ValueError: Bei ungültigen oder fehlenden Pflichtfeldern
    """
    # Pflichtfelder validieren
    for field in ("name", "width", "height", "colors", "layers"):
        if field not in data:
            raise ValueError(f"Pflichtfeld '{field}' fehlt in der Datei")

    width = data["width"]
    height = data["height"]

    # Typ- und Wertevalidierung
    if not isinstance(width, int) or not isinstance(height, int):
        raise ValueError(f"Ungültige Mustergröße: {width}x{height} (int erwartet)")
    if width < 1 or height < 1:
        raise ValueError(f"Ungültige Mustergröße: {width}x{height} (min. 1x1)")
    if width > 2000 or height > 2000:
        raise ValueError(f"Mustergröße zu groß: {width}x{height} (max. 2000x2000)")
    if not isinstance(data["colors"], list):
        raise ValueError("Ungültiges Farbformat: Liste erwartet")
    if not isinstance(data["layers"], list) or len(data["layers"]) == 0:
        raise ValueError("Mindestens ein Layer erforderlich")

    # fabric_count wird an mehreren Stellen (info_panel.py, pattern.py::size_cm)
    # als Divisor benutzt -- eine beschaedigte/handbearbeitete .pxs-Datei mit
    # fabric_count<=0 wuerde dort einen ZeroDivisionError ausloesen. Kein
    # Loeschen/Ablehnen der Datei noetig, einfacher Fallback reicht (gleiche
    # Grosszuegigkeit wie bei width/height oben).
    loaded_fabric_count = data.get("fabric_count", DEFAULT_FABRIC_COUNT)
    # json.load() akzeptiert per Default die nicht-standardkonformen Literale
    # NaN/Infinity/-Infinity -- `nan <= 0` und `inf <= 0` sind beide False in
    # Python, wuerden die reine "<=0"-Pruefung also unbemerkt durchrutschen
    # und stillschweigend NaN-Groessen (statt eines Crashs) im UI erzeugen.
    if (
        not isinstance(loaded_fabric_count, (int, float))
        or math.isnan(loaded_fabric_count)
        or math.isinf(loaded_fabric_count)
        or loaded_fabric_count <= 0
    ):
        loaded_fabric_count = DEFAULT_FABRIC_COUNT

    # Pattern erstellen
    pattern = Pattern(
        name=data["name"],
        width=width,
        height=height,
        fabric_count=loaded_fabric_count,
        metadata=data.get("metadata", {}),
        # Quell-Infos laden (für Palettenwechsel-Feature)
        source_image_path=data.get("source_image_path"),
        source_image_crop=tuple(data.get("source_image_crop", [0, 0, 1, 1])),
        source_palette_name=data.get("source_palette_name"),
        # Mode: Default "stitch" für ältere Dateien ohne mode-Feld.
        # Unbekannte Werte werden ebenfalls auf "stitch" gemappt.
        mode=data.get("mode", "stitch") if data.get("mode") in ("stitch", "diamond") else "stitch",
    )

    # Farben laden
    pattern.color_entries.clear()
    for color_data in data["colors"]:
        pattern.color_entries.append(_dict_to_color_entry(color_data))

    # Layer laden (über öffentliche API statt direktem _layers/_active_index Zugriff)
    loaded_layers = [_dict_to_layer(ld, width, height) for ld in data["layers"]]
    active = data.get("active_layer", 0)

    pattern.layer_stack = LayerStack(width, height)
    pattern.layer_stack.replace_all_layers(loaded_layers, active)

    # Rückstiche laden (seit v1.1, optional für ältere Dateien)
    pattern.backstitch_manager.clear()
    for bs_data in data.get("backstitches", []):
        bs = _dict_to_backstitch(bs_data)
        pattern.backstitch_manager.add(bs.x1, bs.y1, bs.x2, bs.y2, bs.color_index)

    # Stich-Zählungen pro Farbe aus den tatsächlichen Grids neu berechnen.
    # So bleiben die Werte konsistent, auch wenn die gespeicherte
    # stitch_count-Angabe veraltet ist.
    pattern.recalculate_stitch_counts()

    return pattern


def _color_entry_to_dict(entry: ColorEntry) -> dict[str, Any]:
    """
    Konvertiert einen ColorEntry zu einem Dictionary.

    Args:
        entry: Der zu konvertierende ColorEntry

    Returns:
        Dictionary mit Garn-Informationen und Symbol
    """
    thread = entry.thread
    result: dict[str, Any] = {
        "name": thread.name,
        "color": thread.color.to_hex(),
        "manufacturer": thread.manufacturer,
        "catalog_number": thread.catalog_number,
        "symbol": entry.symbol,
        "stitch_count": entry.stitch_count,
        "skip_stitching": entry.skip_stitching,
        "strands": entry.strands,
        "is_bead": entry.is_bead,
        "is_diamond": entry.is_diamond,
        "color_id": entry.color_id,
    }
    # Tweed-Blends: Komponenten und Strang-Verhältnisse mitspeichern
    if thread.is_blend:
        result["blend_components"] = [
            {
                "name": c.name,
                "color": c.color.to_hex(),
                "manufacturer": c.manufacturer,
                "catalog_number": c.catalog_number,
            }
            for c in (thread.blend_components or [])
        ]
        result["strand_ratios"] = list(thread.strand_ratios or [])
    return result


def _dict_to_color_entry(data: dict[str, Any]) -> ColorEntry:
    """
    Konvertiert ein Dictionary zurück zu einem ColorEntry.

    Args:
        data: Dictionary aus der JSON-Datei

    Returns:
        Rekonstruierter ColorEntry

    Raises:
        ValueError: Bei fehlenden Pflichtfeldern (name, color, symbol)
    """
    for field in ("name", "color", "symbol"):
        if field not in data:
            raise ValueError(f"Farbeintrag: Pflichtfeld '{field}' fehlt")

    hex_color = data["color"]
    if (
        not isinstance(hex_color, str)
        or not hex_color.startswith("#")
        or len(hex_color) not in (4, 7)
    ):
        raise ValueError(f"Ungültige Hex-Farbe: '{hex_color}'")

    thread = Thread.from_hex(
        name=data["name"],
        hex_color=hex_color,
        manufacturer=data.get("manufacturer", ""),
        catalog_number=data.get("catalog_number", ""),
    )

    # Blend-Komponenten rekonstruieren wenn vorhanden
    blend_data = data.get("blend_components")
    if blend_data:
        components = [
            Thread.from_hex(
                name=c["name"],
                hex_color=c["color"],
                manufacturer=c.get("manufacturer", ""),
                catalog_number=c.get("catalog_number", ""),
            )
            for c in blend_data
        ]
        thread.blend_components = components
        thread.strand_ratios = list(data.get("strand_ratios", [1] * len(components)))

    entry = ColorEntry(
        thread=thread,
        symbol=data["symbol"],
        stitch_count=data.get("stitch_count", 0),
        skip_stitching=data.get("skip_stitching", False),
        strands=data.get("strands", 2),
        is_bead=data.get("is_bead", False),
        is_diamond=data.get("is_diamond", False),
    )
    # Aeltere .pxs-Dateien (vor color_id) haben das Feld nicht -- der
    # ColorEntry-Default (frischer uuid4) greift dann automatisch, sonst
    # die gespeicherte Identitaet uebernehmen (wichtig fuer
    # Pattern.convert_to_mode()'s Mode-Backup-Zuordnung ueber einen
    # Speichern/Laden-Zyklus hinweg).
    color_id = data.get("color_id")
    if color_id:
        entry.color_id = color_id
    return entry


def _layer_to_dict(layer: Layer) -> dict[str, Any]:
    """
    Konvertiert ein Layer zu einem Dictionary.

    Stiche werden als kompakte [x, y, color_index] Listen gespeichert,
    nicht als volles Grid, um Speicherplatz zu sparen.

    Args:
        layer: Das zu konvertierende Layer

    Returns:
        Dictionary mit Layer-Metadaten und Stich-Liste
    """
    import numpy as np

    # Stiche als Liste von [x, y, color_index] für kompakte Speicherung
    # Nutze iterate_stitches() für effiziente numpy-Iteration
    stitches = [[x, y, int(color_index)] for x, y, color_index in layer.iterate_stitches()]

    # Erledigte Stiche speichern (seit v1.2)
    completed = []
    if np.any(layer.completion_grid):
        # Nur Positionen wo completion=True UND ein Stich vorhanden ist
        mask = layer.completion_grid & (layer.grid != NO_STITCH)
        positions = np.argwhere(mask)
        completed = [[int(x), int(y)] for y, x in positions]

    # Stichtypen speichern (nur Nicht-FULL Typen, seit v1.3)
    stitch_types = []
    if layer.stitch_type_grid is not None and np.any(layer.stitch_type_grid != 0):
        positions = np.argwhere(layer.stitch_type_grid != 0)
        stitch_types = [[int(x), int(y), int(layer.stitch_type_grid[y, x])] for y, x in positions]

    result = {
        "name": layer.name,
        "visible": layer.visible,
        "locked": layer.locked,
        "opacity": layer.opacity,
        "stitches": stitches,
        "completed_stitches": completed,
    }
    if stitch_types:
        result["stitch_types"] = stitch_types
    # Notiz nur schreiben wenn nicht-leer (hält Datei kompakt, seit v1.4)
    if layer.note:
        result["note"] = layer.note
    return result


def _dict_to_layer(data: dict[str, Any], width: int, height: int) -> Layer:
    """
    Konvertiert ein Dictionary zurück zu einem Layer.

    Erstellt ein leeres Grid und setzt dann die gespeicherten Stiche.

    Args:
        data: Dictionary aus der JSON-Datei
        width: Breite des Layers
        height: Höhe des Layers

    Returns:
        Rekonstruiertes Layer mit numpy-Grid
    """
    layer = Layer(
        name=data["name"],
        width=width,
        height=height,
    )
    layer.visible = data.get("visible", True)
    # WICHTIG: locked NICHT vor dem Laden setzen — sonst lehnt set_stitch
    # alle Stiche ab und der Layer landet leer. Wird unten gesetzt.
    saved_locked = bool(data.get("locked", False))
    layer.opacity = data.get("opacity", 1.0)
    layer.note = data.get("note", "")

    # Stiche laden (mit Validierung)
    for stitch in data.get("stitches", []):
        if not isinstance(stitch, (list, tuple)) or len(stitch) < 3:
            continue  # Ungültigen Stich überspringen
        try:
            x, y, color_index = int(stitch[0]), int(stitch[1]), int(stitch[2])
            layer.set_stitch(x, y, color_index)
        except (ValueError, TypeError):
            continue  # Nicht-numerische Werte überspringen

    # Erledigte Stiche laden (seit v1.2, optional für ältere Dateien)
    for pos in data.get("completed_stitches", []):
        if not isinstance(pos, (list, tuple)) or len(pos) < 2:
            continue
        try:
            x, y = int(pos[0]), int(pos[1])
            if 0 <= x < width and 0 <= y < height:
                layer.completion_grid[y, x] = True
        except (ValueError, TypeError):
            continue

    # Stichtypen laden (seit v1.3, optional für ältere Dateien)
    # 0..9 = klassische Typen, 10 = Bead (seit v1.4), 11 = Diamond (seit v1.5)
    for entry in data.get("stitch_types", []):
        if not isinstance(entry, (list, tuple)) or len(entry) < 3:
            continue
        try:
            x, y, stype = int(entry[0]), int(entry[1]), int(entry[2])
            if 0 <= x < width and 0 <= y < height and 0 <= stype <= 11:
                layer.stitch_type_grid[y, x] = stype
        except (ValueError, TypeError):
            continue

    # Locked-Flag erst NACH dem Laden setzen — sonst würden alle set_stitch-
    # Aufrufe oben silent fehlschlagen und der Layer landet leer.
    layer.locked = saved_locked

    return layer


def _backstitch_to_dict(backstitch: Backstitch) -> dict[str, Any]:
    """
    Konvertiert einen Backstitch zu einem Dictionary.

    Args:
        backstitch: Der zu konvertierende Backstitch

    Returns:
        Dictionary mit Start-/Endkoordinaten und Farbe
    """
    return {
        "x1": backstitch.x1,
        "y1": backstitch.y1,
        "x2": backstitch.x2,
        "y2": backstitch.y2,
        "color_index": backstitch.color_index,
    }


def _dict_to_backstitch(data: dict[str, Any]) -> Backstitch:
    """
    Konvertiert ein Dictionary zurück zu einem Backstitch.

    Args:
        data: Dictionary aus der JSON-Datei

    Returns:
        Rekonstruiertes Backstitch-Objekt

    Raises:
        ValueError: Bei fehlenden Pflichtfeldern (x1, y1, x2, y2, color_index)
    """
    for field in ("x1", "y1", "x2", "y2", "color_index"):
        if field not in data:
            raise ValueError(f"Rückstich: Pflichtfeld '{field}' fehlt")

    return Backstitch(
        x1=data["x1"],
        y1=data["y1"],
        x2=data["x2"],
        y2=data["y2"],
        color_index=data["color_index"],
    )
