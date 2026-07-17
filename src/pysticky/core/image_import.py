"""
Bildimport für PySticky.

Konvertiert Bilder zu Kreuzstich-Mustern mit Farbquantisierung.
"""

from dataclasses import dataclass
from pathlib import Path

try:
    import numpy as np
    from PIL import Image

    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

from .palette import get_palette_manager
from .pattern import SYMBOLS, ColorEntry, Pattern
from .thread import Thread


@dataclass
class ImportSettings:
    """Einstellungen für den Bildimport."""

    width: int = 50
    height: int = 50
    max_colors: int = 20
    palette_name: str = "DMC"
    dithering: bool = False
    dithering_mode: str = "none"  # "none", "floyd_steinberg", "ordered"
    quantization_method: str = "nearest"  # "nearest", "median_cut"
    keep_aspect_ratio: bool = True
    auto_backstitches: bool = False

    # Pre-Import-Bildanpassung (vor Quantisierung). 1.0 = unverändert.
    brightness: float = 1.0  # 0.0 = schwarz, 2.0 = sehr hell
    contrast: float = 1.0  # 0.0 = grau, 2.0 = sehr kontrastreich
    saturation: float = 1.0  # 0.0 = Graustufen, 2.0 = sehr saturiert

    # Confetti-Reduction nach der Quantisierung. min_run_size <= 1 = aus.
    # Sinnvolle Werte: 2-5. Bei >=2 werden isolierte Einzelpixel der
    # dominanten Nachbarfarbe zugeordnet, über 3 verschwinden auch
    # kleine Cluster. Praxis-Empfehlung: 2 für dezente, 3 für aggressive
    # Reduktion bei foto-realistischen Mustern.
    confetti_min_run_size: int = 1

    def __post_init__(self):
        """Synchronisiert dithering bool mit dithering_mode."""
        # Backwards-Kompatibilität: wenn nur dithering=True gesetzt wurde
        if self.dithering and self.dithering_mode == "none":
            self.dithering_mode = "floyd_steinberg"
        # Vorwärts-Sync: mode → bool
        if self.dithering_mode != "none":
            self.dithering = True

    @property
    def has_adjustments(self) -> bool:
        """True wenn Helligkeit/Kontrast/Sättigung != 1.0 (also etwas anzupassen ist)."""
        return self.brightness != 1.0 or self.contrast != 1.0 or self.saturation != 1.0


def check_pillow_available() -> bool:
    """Prüft ob Pillow verfügbar ist."""
    return HAS_PILLOW


def import_image(
    image_path: Path | str,
    settings: ImportSettings,
    crop: tuple[float, float, float, float] = (0, 0, 1, 1),
) -> Pattern:
    """
    Importiert ein Bild und konvertiert es zu einem Kreuzstich-Muster.

    Args:
        image_path: Pfad zum Bild
        settings: Import-Einstellungen
        crop: Ausschnitt (x1, y1, x2, y2) normalisiert 0-1

    Returns:
        Das generierte Pattern
    """
    if not HAS_PILLOW:
        raise ImportError(
            "Pillow und numpy sind erforderlich. Installiere mit: pip install Pillow numpy"
        )

    image_path = Path(image_path)

    try:
        # Basistyp annotieren: open() liefert ImageFile, spätere convert()-
        # Zuweisungen liefern Image.Image (Basisklasse) — sonst Typkonflikt.
        image: Image.Image = Image.open(str(image_path))
    except OSError as e:
        raise ValueError(f"Bild konnte nicht geöffnet werden: {e}")

    # In RGB konvertieren
    if image.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode == "P":
            image = image.convert("RGBA")
        if image.mode in ("RGBA", "LA"):
            background.paste(image, mask=image.split()[-1])
            image = background
        else:
            image = image.convert("RGB")
    elif image.mode != "RGB":
        image = image.convert("RGB")

    # Ausschnitt anwenden
    x1, y1, x2, y2 = crop
    if x1 > 0 or y1 > 0 or x2 < 1 or y2 < 1:
        left = int(x1 * image.width)
        top = int(y1 * image.height)
        right = int(x2 * image.width)
        bottom = int(y2 * image.height)

        # Mindestgröße sicherstellen
        right = max(right, left + 1)
        bottom = max(bottom, top + 1)

        image = image.crop((left, top, right, bottom))

    # Helligkeit / Kontrast / Sättigung vor der Quantisierung anpassen,
    # damit die Farbwahl auf dem bearbeiteten Bild basiert.
    if settings.has_adjustments:
        from PIL import ImageEnhance

        if settings.brightness != 1.0:
            image = ImageEnhance.Brightness(image).enhance(settings.brightness)
        if settings.contrast != 1.0:
            image = ImageEnhance.Contrast(image).enhance(settings.contrast)
        if settings.saturation != 1.0:
            image = ImageEnhance.Color(image).enhance(settings.saturation)

    # Größe berechnen
    target_width = settings.width
    target_height = settings.height

    if settings.keep_aspect_ratio:
        orig_ratio = image.width / image.height
        target_ratio = target_width / target_height

        if orig_ratio > target_ratio:
            target_height = max(1, int(target_width / orig_ratio))
        else:
            target_width = max(1, int(target_height * orig_ratio))

    target_width = max(1, target_width)
    target_height = max(1, target_height)

    # Bild skalieren
    image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)

    # Garnpalette laden
    palette_manager = get_palette_manager()
    palette = palette_manager.get_palette(settings.palette_name)

    if not palette:
        raise ValueError(f"Palette '{settings.palette_name}' nicht gefunden")

    thread_list = list(palette.threads)

    # Farben quantisieren
    pixels = np.array(image)

    # Farbauswahl: Median-Cut oder Standard
    if settings.quantization_method == "median_cut":
        selected_threads = _select_colors_median_cut(pixels, thread_list, settings.max_colors)
    else:
        selected_threads = None  # wird von _quantize_simple intern bestimmt

    # Dithering-Modus auswählen
    if settings.dithering_mode == "floyd_steinberg":
        quantized, used_threads = _quantize_with_dithering(
            pixels,
            thread_list,
            settings.max_colors,
            preselected_threads=selected_threads,
        )
    elif settings.dithering_mode == "ordered":
        quantized, used_threads = _quantize_with_ordered_dithering(
            pixels,
            thread_list,
            settings.max_colors,
            preselected_threads=selected_threads,
        )
    else:
        quantized, used_threads = _quantize_simple(
            pixels,
            thread_list,
            settings.max_colors,
            preselected_threads=selected_threads,
        )

    # Palette-Modus erkennen: wenn der User eine DP-/Bead-Palette gewählt
    # hat, soll das Pattern direkt im richtigen Modus angelegt werden, plus
    # die ColorEntries müssen das passende is_diamond/is_bead-Flag tragen,
    # damit der DP-Mode-Switch + Drill-Rendering greifen.
    # Modul-level get_palette_manager-Import schon vorhanden (oben).
    pm = get_palette_manager()
    src_palette = pm.get_palette(settings.palette_name)
    palette_is_diamond = bool(src_palette and src_palette.is_diamond)
    palette_is_beads = bool(src_palette and src_palette.is_beads)
    pattern_mode = "diamond" if palette_is_diamond else "stitch"
    # DP-Default: 10 (= 2.5mm Drill-Pitch). Sonst: Aida-Default (14).
    default_fabric = 10 if palette_is_diamond else 14

    # Pattern erstellen
    pattern = Pattern(
        name=image_path.stem,
        width=target_width,
        height=target_height,
        fabric_count=default_fabric,
        mode=pattern_mode,
        # Quell-Infos speichern für späteren Palettenwechsel
        source_image_path=str(image_path.absolute()),
        source_image_crop=crop,
        source_palette_name=settings.palette_name,
        metadata={
            "dithering": settings.dithering,
            "dithering_mode": settings.dithering_mode,
            "quantization_method": settings.quantization_method,
            "max_colors": settings.max_colors,
            "auto_backstitches": settings.auto_backstitches,
            "confetti_min_run_size": settings.confetti_min_run_size,
            "keep_aspect_ratio": settings.keep_aspect_ratio,
            "brightness": settings.brightness,
            "contrast": settings.contrast,
            "saturation": settings.saturation,
        },
    )
    pattern.color_entries.clear()

    # Farben hinzufügen — DP/Bead-Flags pro Entry setzen, damit
    # set_stitch() automatisch den richtigen Stitch-Type erzeugt.
    thread_to_index: dict[str, int] = {}
    for i, thread in enumerate(used_threads):
        symbol = SYMBOLS[i % len(SYMBOLS)]
        entry = ColorEntry(
            thread=thread,
            symbol=symbol,
            stitch_count=0,
            is_diamond=palette_is_diamond,
            is_bead=palette_is_beads,
        )
        pattern.color_entries.append(entry)
        key = f"{thread.manufacturer}_{thread.catalog_number}"
        thread_to_index[key] = i

    # Vor dem Setzen: Quantisiertes Ergebnis als Index-Grid aufbauen,
    # Confetti reduzieren, dann ins Layer schreiben.
    from .layer import NO_STITCH as _NO_STITCH

    index_grid = np.full((target_height, target_width), _NO_STITCH, dtype=np.int16)
    for y in range(target_height):
        for x in range(target_width):
            cell_thread = quantized[y][x]
            if cell_thread:
                key = f"{cell_thread.manufacturer}_{cell_thread.catalog_number}"
                color_index = thread_to_index.get(key)
                if color_index is not None:
                    index_grid[y, x] = color_index

    if settings.confetti_min_run_size > 1:
        from .confetti_reduction import reduce_confetti

        index_grid = reduce_confetti(index_grid, settings.confetti_min_run_size)

    # Stiche ins Layer schreiben und Stitch-Counts zählen
    layer = pattern.active_layer
    if layer is None:  # frisch erzeugtes Pattern hat immer ein aktives Layer
        raise RuntimeError("Pattern ohne aktives Layer — Import-Invariante verletzt")
    for y in range(target_height):
        for x in range(target_width):
            color_index = int(index_grid[y, x])
            if color_index != _NO_STITCH:
                layer.set_stitch(x, y, color_index)
                pattern.color_entries[color_index].stitch_count += 1

    # Backstitch-Auto-Generierung per Kantenerkennung
    if settings.auto_backstitches:
        try:
            backstitches = generate_backstitches_from_edges(image_path, target_width, target_height)
            if backstitches:
                # Backstitch-Farbe: dunkelste vorhandene Farbe
                bs_color_idx = _find_darkest_color_index(pattern)
                for x1, y1, x2, y2 in backstitches:
                    pattern.add_backstitch(x1, y1, x2, y2, bs_color_idx)
        except (ImportError, OSError, ValueError):
            pass  # Backstitch-Erkennung ist optional

    return pattern


def _quantize_simple(
    pixels: np.ndarray,
    thread_list: list[Thread],
    max_colors: int,
    preselected_threads: list[Thread] | None = None,
) -> tuple[list[list[Thread | None]], list[Thread]]:
    """
    Einfache Farbquantisierung ohne Dithering (speicher-optimiert).

    Verarbeitet Pixel batch-weise um Memory-Probleme bei großen Bildern
    zu vermeiden. Vorher: O(N_pixels * N_colors) RAM auf einmal.
    Jetzt: O(BATCH_SIZE * N_colors) RAM pro Batch.

    Args:
        preselected_threads: Vorab gewählte Farben (z.B. per Median-Cut).
            Wenn gesetzt, werden nur diese Farben verwendet.
    """
    height, width = pixels.shape[:2]

    if preselected_threads:
        # Nur die vorgewählten Farben als Palette verwenden
        work_threads = preselected_threads
        work_colors = np.array(
            [[t.color.r, t.color.g, t.color.b] for t in work_threads], dtype=np.float64
        )
        pixels_flat = pixels.reshape(-1, 3).astype(np.float64)
        n_pixels = pixels_flat.shape[0]

        BATCH_SIZE = 10000
        nearest_indices = np.empty(n_pixels, dtype=np.int32)
        for start in range(0, n_pixels, BATCH_SIZE):
            end = min(start + BATCH_SIZE, n_pixels)
            batch = pixels_flat[start:end]
            diff = batch[:, np.newaxis, :] - work_colors[np.newaxis, :, :]
            distances_sq = np.sum(diff**2, axis=2)
            nearest_indices[start:end] = np.argmin(distances_sq, axis=1)

        nearest_indices = nearest_indices.reshape(height, width)  # type: ignore[assignment]
        final_result: list[list[Thread | None]] = []
        for y in range(height):
            row: list[Thread | None] = []
            for x in range(width):
                row.append(work_threads[nearest_indices[y, x]])
            final_result.append(row)
        return final_result, work_threads

    # Standard-Pfad: volle Palette, Top-N Auswahl
    palette_colors = np.array(
        [[t.color.r, t.color.g, t.color.b] for t in thread_list], dtype=np.float64
    )

    pixels_flat = pixels.reshape(-1, 3).astype(np.float64)
    n_pixels = pixels_flat.shape[0]

    # Batch-weise nächste Farbe berechnen um RAM zu schonen
    # Bei 500x500 Bild + 400 Farben wäre die volle Matrix ~2.4 GB
    # Mit Batch-Größe 10000 nur ~9.6 MB pro Batch
    BATCH_SIZE = 10000
    nearest_indices = np.empty(n_pixels, dtype=np.int32)

    for start in range(0, n_pixels, BATCH_SIZE):
        end = min(start + BATCH_SIZE, n_pixels)
        batch = pixels_flat[start:end]

        # Squared distances (sqrt nicht nötig für argmin)
        diff = batch[:, np.newaxis, :] - palette_colors[np.newaxis, :, :]
        distances_sq = np.sum(diff**2, axis=2)
        nearest_indices[start:end] = np.argmin(distances_sq, axis=1)

    nearest_indices = nearest_indices.reshape(height, width)  # type: ignore[assignment]

    # Zähle Farbverwendung
    unique, counts = np.unique(nearest_indices, return_counts=True)
    color_usage = {int(idx): int(cnt) for idx, cnt in zip(unique, counts)}

    # Top N Farben bestimmen
    sorted_colors = sorted(color_usage.items(), key=lambda x: x[1], reverse=True)
    top_indices = set(idx for idx, _ in sorted_colors[:max_colors])

    # Mapping: nicht-top Farben → nächste top Farbe (vorab berechnen statt pro Pixel)
    top_list = list(top_indices)
    top_colors = palette_colors[top_list]

    remap = {}
    all_used_indices = set(int(idx) for idx in unique)
    for idx in all_used_indices:
        if idx in top_indices:
            remap[idx] = idx
        else:
            target = palette_colors[idx]
            dists = np.sum((top_colors - target) ** 2, axis=1)
            remap[idx] = top_list[int(np.argmin(dists))]

    # Vektorisiertes Remapping mit numpy (statt Python-Loop pro Pixel)
    remap_array = np.arange(len(thread_list), dtype=np.int32)
    for old_idx, new_idx in remap.items():
        remap_array[old_idx] = new_idx

    final_indices = remap_array[nearest_indices]

    # Ergebnis als Listen erstellen
    used_threads = [thread_list[idx] for idx in top_indices]

    final_result = []
    for y in range(height):
        row = []
        for x in range(width):
            row.append(thread_list[final_indices[y, x]])
        final_result.append(row)

    return final_result, used_threads


def _quantize_with_dithering(
    pixels: np.ndarray,
    thread_list: list[Thread],
    max_colors: int,
    preselected_threads: list[Thread] | None = None,
) -> tuple[list[list[Thread | None]], list[Thread]]:
    """Floyd-Steinberg Dithering."""
    height, width = pixels.shape[:2]

    if preselected_threads:
        top_threads = preselected_threads
    else:
        _, top_threads = _quantize_simple(pixels, thread_list, max_colors)
    top_colors = np.array(
        [[t.color.r, t.color.g, t.color.b] for t in top_threads], dtype=np.float64
    )

    working = pixels.astype(np.float64)
    result: list[list[Thread | None]] = []

    for y in range(height):
        row: list[Thread | None] = []
        for x in range(width):
            old_pixel = working[y, x].copy()

            distances = np.sqrt(np.sum((top_colors - old_pixel) ** 2, axis=1))
            nearest_idx = int(np.argmin(distances))
            new_pixel = top_colors[nearest_idx]

            row.append(top_threads[nearest_idx])

            error = old_pixel - new_pixel

            if x + 1 < width:
                working[y, x + 1] = np.clip(working[y, x + 1] + error * 7 / 16, 0, 255)
            if y + 1 < height:
                if x > 0:
                    working[y + 1, x - 1] = np.clip(working[y + 1, x - 1] + error * 3 / 16, 0, 255)
                working[y + 1, x] = np.clip(working[y + 1, x] + error * 5 / 16, 0, 255)
                if x + 1 < width:
                    working[y + 1, x + 1] = np.clip(working[y + 1, x + 1] + error * 1 / 16, 0, 255)

        result.append(row)

    return result, top_threads


def _quantize_with_ordered_dithering(
    pixels: np.ndarray,
    thread_list: list[Thread],
    max_colors: int,
    preselected_threads: list[Thread] | None = None,
) -> tuple[list[list[Thread | None]], list[Thread]]:
    """
    Ordered (Bayer) Dithering.

    Verwendet eine 4×4 Bayer-Matrix als Schwellwert-Map.
    Erzeugt ein gleichmäßiges Raster-Muster statt organischer Streuung.
    """
    height, width = pixels.shape[:2]

    if preselected_threads:
        top_threads = preselected_threads
    else:
        _, top_threads = _quantize_simple(pixels, thread_list, max_colors)
    top_colors = np.array(
        [[t.color.r, t.color.g, t.color.b] for t in top_threads], dtype=np.float64
    )

    # 4×4 Bayer-Matrix (normalisiert auf [-0.5, 0.5] Bereich, dann skaliert)
    bayer_4x4 = np.array(
        [
            [0, 8, 2, 10],
            [12, 4, 14, 6],
            [3, 11, 1, 9],
            [15, 7, 13, 5],
        ],
        dtype=np.float64,
    )
    # Normalisieren: (M / 16 - 0.5) * spread_factor
    spread = 32.0
    bayer_normalized = (bayer_4x4 / 16.0 - 0.5) * spread

    # Bayer-Matrix über das gesamte Bild kacheln
    tiled_y = np.tile(bayer_normalized, (height // 4 + 1, width // 4 + 1))
    tiled = tiled_y[:height, :width]

    # Schwellwert auf alle 3 Kanäle anwenden
    working = pixels.astype(np.float64)
    for c in range(3):
        working[:, :, c] = np.clip(working[:, :, c] + tiled, 0, 255)

    # Jetzt einfache Quantisierung auf den adjustierten Pixeln
    pixels_flat = working.reshape(-1, 3)
    n_pixels = pixels_flat.shape[0]

    BATCH_SIZE = 10000
    nearest_indices = np.empty(n_pixels, dtype=np.int32)
    for start in range(0, n_pixels, BATCH_SIZE):
        end = min(start + BATCH_SIZE, n_pixels)
        batch = pixels_flat[start:end]
        diff = batch[:, np.newaxis, :] - top_colors[np.newaxis, :, :]
        distances_sq = np.sum(diff**2, axis=2)
        nearest_indices[start:end] = np.argmin(distances_sq, axis=1)

    nearest_indices = nearest_indices.reshape(height, width)  # type: ignore[assignment]

    result: list[list[Thread | None]] = []
    for y in range(height):
        row: list[Thread | None] = []
        for x in range(width):
            row.append(top_threads[nearest_indices[y, x]])
        result.append(row)

    return result, top_threads


def _select_colors_median_cut(
    pixels: np.ndarray,
    thread_list: list[Thread],
    max_colors: int,
) -> list[Thread]:
    """
    Median-Cut Farbquantisierung zur besseren Farbauswahl.

    Rekursive Box-Zerlegung: Findet den Kanal mit der größten Spanne,
    teilt am Median, bis max_colors Boxen entstehen.
    Jede Box → Durchschnittsfarbe → nächsten Thread aus Palette finden.

    Ergebnis: Bessere Farbverteilung als reine Häufigkeitsauswahl.
    """
    pixels_flat = pixels.reshape(-1, 3).astype(np.float64)

    # Initiale Box: alle Pixel
    boxes: list[np.ndarray] = [pixels_flat]

    # Iterativ splitten bis genug Boxen
    while len(boxes) < max_colors:
        # Box mit größter Spanne finden
        best_idx = -1
        best_range = -1.0
        best_channel = 0

        for i, box in enumerate(boxes):
            if len(box) < 2:
                continue
            for ch in range(3):
                ch_range = float(np.max(box[:, ch]) - np.min(box[:, ch]))
                if ch_range > best_range:
                    best_range = ch_range
                    best_idx = i
                    best_channel = ch

        if best_idx < 0 or best_range <= 0:
            break  # Keine Box mehr teilbar

        # Am Median des besten Kanals splitten
        box = boxes.pop(best_idx)
        median_val = np.median(box[:, best_channel])
        mask = box[:, best_channel] < median_val
        left = box[mask]
        right = box[~mask]

        # Fallback bei degeneriertem Split (z.B. np.median == min, sodass
        # `<` keinen Pixel matched): splitten am arithmetischen Mittel
        # zwischen min und max. Da `best_range > 0`, ist min < max
        # garantiert -> beide Hälften nicht-leer.
        if len(left) == 0 or len(right) == 0:
            mid = (float(np.min(box[:, best_channel])) + float(np.max(box[:, best_channel]))) / 2.0
            mask = box[:, best_channel] < mid
            left = box[mask]
            right = box[~mask]

        # Nur zurückpacken wenn echt geteilt wurde — sonst Endlosschleife.
        if len(left) > 0 and len(right) > 0:
            boxes.append(left)
            boxes.append(right)
        else:
            # Box ist nicht splittbar (defensive — sollte nach Mean-Fallback
            # nie passieren, aber bewahrt uns vor Hang im Pathologie-Fall).
            break

    # Durchschnittsfarbe jeder Box → nächsten Thread finden
    palette_colors = np.array(
        [[t.color.r, t.color.g, t.color.b] for t in thread_list], dtype=np.float64
    )

    selected_threads: list[Thread] = []
    used_indices: set[int] = set()

    for box in boxes:
        avg_color = np.mean(box, axis=0)
        dists = np.sum((palette_colors - avg_color) ** 2, axis=1)
        # Sortiere nach Distanz und nimm den nächsten noch nicht verwendeten
        sorted_indices = np.argsort(dists)
        for idx in sorted_indices:
            idx_int = int(idx)
            if idx_int not in used_indices:
                selected_threads.append(thread_list[idx_int])
                used_indices.add(idx_int)
                break
        else:
            # Fallback: nächsten Thread nehmen (auch wenn doppelt)
            selected_threads.append(thread_list[int(sorted_indices[0])])

    return selected_threads


def generate_backstitches_from_edges(
    image_path: Path | str,
    target_width: int,
    target_height: int,
    threshold: float = 0.3,
) -> list[tuple[int, int, int, int]]:
    """
    Erkennt Kanten in einem Bild per Sobel-Operator und generiert Backstitch-Segmente.

    Args:
        image_path: Pfad zum Quellbild
        target_width: Breite des Musters (in Stichen)
        target_height: Höhe des Musters (in Stichen)
        threshold: Schwellwert für Kantenerkennung (0-1, relativ zum Maximum)

    Returns:
        Liste von Backstitch-Segmenten als (x1*2, y1*2, x2*2, y2*2)
        (im Backstitch-Koordinatensystem: 2× Auflösung)
    """
    if not HAS_PILLOW:
        return []

    image = Image.open(str(image_path)).convert("L")  # Graustufen
    image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)

    img_array = np.array(image, dtype=np.float64) / 255.0

    # Sobel-Operator (3×3 Kernel, manuelle 2D-Faltung)
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float64)
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float64)

    h, w = img_array.shape
    gx = np.zeros_like(img_array)
    gy = np.zeros_like(img_array)

    # Manuelle 2D-Faltung (pure numpy, ohne scipy)
    padded = np.pad(img_array, 1, mode="edge")
    for dy in range(3):
        for dx in range(3):
            gx += sobel_x[dy, dx] * padded[dy : dy + h, dx : dx + w]
            gy += sobel_y[dy, dx] * padded[dy : dy + h, dx : dx + w]

    # Kantenstärke
    edge_magnitude = np.sqrt(gx**2 + gy**2)

    # Normalisieren und Schwellwert anwenden.
    # Achtung: bei uniformen Bildern produziert Sobel nur Float-Rauschen
    # in Größenordnung 1e-16. Würden wir hier durch dieses Rauschen
    # teilen, würde der relative Threshold dieses Rauschen zu echten
    # Kanten "verstärken" — daher epsilon-Floor.
    max_mag = float(np.max(edge_magnitude))
    if max_mag > 1e-6:
        edge_magnitude /= max_mag
        edge_mask = edge_magnitude > threshold
    else:
        # Praktisch keine Kanten im Bild
        edge_mask = np.zeros_like(edge_magnitude, dtype=bool)

    # Kanten-Pixel zu Backstitch-Segmenten verbinden
    backstitches: list[tuple[int, int, int, int]] = []

    # Für jedes Kanten-Pixel: Verbindungen zu benachbarten Kanten-Pixeln
    # Im Backstitch-System: Pixel (x,y) → Koordinate (x*2, y*2)
    directions = [(1, 0), (0, 1), (1, 1), (1, -1)]  # rechts, unten, diagonal

    for y in range(h):
        for x in range(w):
            if not edge_mask[y, x]:
                continue
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and edge_mask[ny, nx]:
                    # Backstitch-Koordinaten (2× Auflösung)
                    bx1, by1 = x * 2, y * 2
                    bx2, by2 = nx * 2, ny * 2
                    backstitches.append((bx1, by1, bx2, by2))

    return backstitches


def _find_darkest_color_index(pattern: Pattern) -> int:
    """Findet den Index der dunkelsten Farbe im Muster."""
    darkest_idx = 0
    darkest_luminance = float("inf")

    for i, entry in enumerate(pattern.color_entries):
        c = entry.thread.color
        # Relative Luminanz (vereinfacht)
        lum = 0.299 * c.r + 0.587 * c.g + 0.114 * c.b
        if lum < darkest_luminance:
            darkest_luminance = lum
            darkest_idx = i

    return darkest_idx


def get_image_info(image_path: Path | str) -> dict:
    """Gibt Informationen über ein Bild zurück."""
    if not HAS_PILLOW:
        raise ImportError("Pillow ist erforderlich")

    image = Image.open(str(image_path))
    return {
        "width": image.width,
        "height": image.height,
        "format": image.format or "Unknown",
        "mode": image.mode,
    }


def create_preview(
    image_path: Path | str,
    settings: ImportSettings,
    preview_size: int = 200,
    crop: tuple[float, float, float, float] = (0, 0, 1, 1),
) -> "Image.Image":
    """
    Erstellt eine Vorschau des importierten Musters.

    Verwendet numpy-Array statt putpixel() für drastisch bessere Performance.
    Vorher: O(width * height * cell_size²) putpixel-Aufrufe
    Jetzt: Ein numpy-Array → Image.fromarray() + resize
    """
    if not HAS_PILLOW:
        raise ImportError("Pillow ist erforderlich")

    pattern = import_image(image_path, settings, crop)

    # Farb-Lookup-Array erstellen: color_index → (R, G, B)
    bg_color = np.array([250, 250, 245], dtype=np.uint8)
    color_lut = np.zeros((len(pattern.color_entries) + 1, 3), dtype=np.uint8)
    for i, entry in enumerate(pattern.color_entries):
        color_lut[i] = [entry.thread.color.r, entry.thread.color.g, entry.thread.color.b]

    # Grid als numpy-Array holen
    layer = pattern.active_layer
    if layer is None:  # Pattern hat hier immer ein aktives Layer
        raise RuntimeError("Pattern ohne aktives Layer — Import-Invariante verletzt")
    grid = layer.grid.copy()

    # Pixel-Array erstellen: Hintergrundfarbe als Default
    pixel_array = np.full((pattern.height, pattern.width, 3), bg_color, dtype=np.uint8)

    # Nur gefüllte Zellen einfärben (vektorisiert)
    from .layer import NO_STITCH

    filled_mask = grid != NO_STITCH
    if np.any(filled_mask):
        filled_indices = grid[filled_mask]
        pixel_array[filled_mask] = color_lut[filled_indices]

    # Als Image erstellen und auf Preview-Größe skalieren
    small_img = Image.fromarray(pixel_array, "RGB")

    cell_size = max(1, preview_size // max(pattern.width, pattern.height))
    img_width = pattern.width * cell_size
    img_height = pattern.height * cell_size

    preview = small_img.resize((img_width, img_height), Image.Resampling.NEAREST)
    return preview


def change_palette(pattern: Pattern, new_palette_name: str) -> Pattern | None:
    """
    Wechselt die Palette eines Musters und berechnet es neu.

    Funktioniert nur für Muster, die aus einem Bild importiert wurden
    und deren Quell-Infos noch vorhanden sind.

    Args:
        pattern: Das bestehende Muster
        new_palette_name: Name der neuen Palette

    Returns:
        Neues Pattern mit der neuen Palette, oder None wenn kein Quellbild
    """
    # Prüfen ob Quellbild vorhanden
    if not pattern.source_image_path:
        return None

    source_path = Path(pattern.source_image_path)
    if not source_path.exists():
        return None

    # Original-Einstellungen aus Metadaten holen (neu + alt kompatibel)
    dithering = pattern.metadata.get("dithering", False)
    dithering_mode = pattern.metadata.get("dithering_mode", "")
    if not dithering_mode:
        # Alt-Format: bool → mode
        dithering_mode = "floyd_steinberg" if dithering else "none"
    quantization_method = pattern.metadata.get("quantization_method", "nearest")
    max_colors = pattern.metadata.get("max_colors", len(pattern.color_entries))
    auto_backstitches = pattern.metadata.get("auto_backstitches", False)
    confetti_min_run_size = pattern.metadata.get("confetti_min_run_size", 1)

    # Neue Import-Einstellungen mit gleichen Parametern
    settings = ImportSettings(
        width=pattern.width,
        height=pattern.height,
        max_colors=max_colors,
        palette_name=new_palette_name,
        dithering_mode=dithering_mode,
        quantization_method=quantization_method,
        keep_aspect_ratio=False,  # Größe exakt beibehalten
        auto_backstitches=auto_backstitches,
        confetti_min_run_size=confetti_min_run_size,
    )

    # Neu importieren
    new_pattern = import_image(source_path, settings, pattern.source_image_crop)

    # Name beibehalten
    new_pattern.name = pattern.name

    return new_pattern


def can_change_palette(pattern: Pattern) -> bool:
    """
    Prüft ob für das Muster ein Palettenwechsel möglich ist.

    Returns:
        True wenn Quellbild vorhanden und existiert
    """
    if not pattern.source_image_path:
        return False

    return Path(pattern.source_image_path).exists()
