# Canvas-Modul

Das Canvas-Modul ist in modulare Mixins aufgeteilt — frueher ~1500 LOC
monolithisch, heute pro Concern eine Datei.

## Dateistruktur

```
canvas/
├── __init__.py              # Paket-Exports
├── enums.py                 # MirrorMode Enum
├── cache.py                 # CanvasCache (Farb-/Font-Cache)
├── canvas.py                # CrossStitchCanvas — Basis-Klasse, kombiniert die Mixins
├── optimized_canvas.py      # OptimizedCrossStitchCanvas — mit Chunk-Caching (im UI aktiv)
├── performance.py           # PerformanceManager (Chunk-Pixmap-Cache) + LOD-Utilities
└── mixins/
    ├── __init__.py
    ├── coordinates_mixin.py # Koordinaten-Umrechnung, Viewport
    ├── mirror_mixin.py      # Spiegelmodus
    ├── rendering_mixin.py   # Alle _draw_* Methoden
    ├── zoom_mixin.py        # Zoom-Funktionen
    ├── events_mixin.py      # Maus- und Tastatur-Events
    └── properties_mixin.py  # Property-Definitionen
```

## Mixin-Verantwortlichkeiten

### CoordinatesMixin
- `_screen_to_grid()` / `_grid_to_screen()` — Koordinaten-Konvertierung
- `_is_valid_grid_pos()` — Positions-Validierung
- `_center_pattern()` — Pattern zentrieren
- `_get_visible_grid_rect()` — Viewport-Culling
- `snap_position()` — Snap-to-Grid

### MirrorMixin
- `get_mirrored_positions()` — Gespiegelte Positionen berechnen
- `_has_mirror_active()` — Spiegelmodus-Check
- `mirror_selection_horizontal()` / `_vertical()` — Auswahl spiegeln

### RenderingMixin
- `paintEvent()` — Hauptzeichenmethode (mit `try/finally` um `QPainter.end()`)
- `_draw_empty_message()`, `_draw_all_cells()`, `_draw_layer_cells()`
- `_draw_grid()`, `_draw_cursor()`, `_draw_center_crosshair()`
- `_draw_mirror_axes()`, `_draw_tool_preview()`, `_draw_backstitches()`
- `_draw_completion_overlay()` — Fortschritts-Markierung

### ZoomMixin
- `zoom_in()` / `zoom_out()` / `zoom_fit()` / `zoom_reset()`
- `set_zoom()` / `get_zoom_percent()`

### EventsMixin
- `wheelEvent()` — Mausrad-Zoom
- `mousePressEvent()` / `mouseMoveEvent()` / `mouseReleaseEvent()` — Klick + Pan
- `leaveEvent()`, `keyPressEvent()`, `resizeEvent()`

### PropertiesMixin
Property-Definitionen fuer alle Ansichtsoptionen:
- `show_grid`, `show_symbols`, `show_colors`, `show_backstitches`
- `show_only_active_layer`, `dim_other_layers`, `show_center_crosshair`
- `mirror_mode`, `mirror_horizontal`, `mirror_vertical`
- Grid-Optionen (Farben, Intervalle), Snap-Optionen

## Verwendung

```python
# Basis-Canvas (Mixins ohne Chunk-Cache)
from pysticky.ui.canvas import CrossStitchCanvas, MirrorMode

# Im UI aktiv: optimierte Variante mit automatischem Chunk-Caching
from pysticky.ui.canvas import OptimizedCrossStitchCanvas
```

`CanvasContainer` (in `widgets/`) instanziiert die Optimized-Variante;
neue Code-Pfade sollten ebenfalls die Optimized-Variante nutzen.

## Performance-Architektur

Alles liegt in `performance.py` (die frueher separate `chunk_cache.py` wurde
entfernt — sie war eine ungenutzte Parallelimplementierung). Drei Bausteine:

1. **`PerformanceManager`** — haelt den Chunk-Pixmap-Cache (Dict pro Chunk-
   Koordinate). Dirty-Tracking via `invalidate_cell()` / `invalidate_region()`
   / `invalidate_all()`, sodass nur betroffene Blocks neu gezeichnet werden.
   `OptimizedCrossStitchCanvas` rendert pro sichtbarem Chunk und cached die
   `QPixmap` (`get_cached_chunk()` / `cache_chunk()`).
2. **`draw_optimized_grid()`** — Batch-Grid-Rendering (eine `drawLines()`-Liste
   statt N einzelne `drawLine()`).
3. **`should_skip_details(cell_size)`** — Level-of-Detail: liefert je nach
   Zellgroesse, ob Symbole / Grid / Details uebersprungen werden.

Auto-Aktivierung ueber `PerformanceManager.check_auto_enable(pattern)` —
einmaliger Schwellwert `LARGE_PATTERN_THRESHOLD` (200×200 = 40.000 Zellen).

### Gemessene Frame-Zeiten (Richtwerte, vom urspruenglichen Benchmark)

| Muster | Ohne Chunk-Cache | Mit Chunk-Cache |
|---|---|---|
| 100×100 | ~5 ms | ~3 ms |
| 200×200 | ~20 ms | ~8 ms |
| 500×500 | ~120 ms | ~15 ms |
| 1000×1000 | ~500 ms | ~25 ms |

### Performance-Stats fuer Debugging

```python
stats = canvas._perf_manager.get_stats()
print(f"Cache Hit Rate: {stats['hit_rate_percent']}%")
print(f"Cached Chunks:  {stats['cached_chunks']}")
print(f"Frame Time:     {stats['last_frame_time_ms']:.1f}ms")
```

Oder Overlay direkt im Canvas anzeigen:

```python
canvas.show_performance_stats = True
```

### Tuning-Hinweise

- **Chunk-Groesse**: Standard 64×64. Bei sehr grossen Mustern (>1000×1000)
  kann 128×128 effizienter sein. Setzbar via
  `canvas.set_chunk_size(128)`.
- **Speicherverbrauch**: Ein 64×64-Chunk bei 20px Zellgroesse braucht
  ~6.5 MB Pixmap (`chunk² · cell² · 4 Bytes`).
- **Invalidierung**: `invalidate_cell()` / `invalidate_region()` markiert
  betroffene Chunks dirty — beim naechsten Repaint werden nur diese neu
  gerendert.
