# Architecture

*[Deutsch](ARCHITECTURE.md) | English*

This document describes the structure of PySticky for new contributors. It
mainly explains the recurring patterns (mixins, theme system, tools) so you
can quickly find your way around the code.

## Overview

PySticky is a **PySide6/Qt** desktop app for designing cross-stitch patterns.
The code is separated into clear layers:

```
src/pysticky/
├── core/        Domain logic — NO Qt UI (Pattern, Layer, Thread, color math, .pxs I/O)
├── io/          Import/export (HTML, PDF, image, bundle, OXS, PAT, XSD)
├── ui/          Qt UI (main window, canvas, panels, tools, dialogs)
├── plugins/     Plugin system (API + built-in plugins)
├── resources/   Palettes (JSON), icons, stylesheets, translations
├── utils/       Cross-cutting helpers (logging, errors)
├── config.py    APP_VERSION (single source of the version) + UI/file defaults
└── main.py      Entry point: main()
```

**Layer rule:** `core` knows neither `io` nor `ui`. `io` may use `core`, but
not `ui`. `ui` may use everything. This keeps the domain logic testable
without a running Qt.

## Entry points

All paths lead to `pysticky.main:main()`:

- `python run.py` — adds `src/` to the path (development)
- `python -m pysticky` — via `__main__.py`
- `pysticky_main.py` — for the PyInstaller build
- `pysticky` (console script from `pyproject.toml`)

## The Mixin Pattern

Large Qt classes are broken down into thematic units via **mixins**, instead
of growing into 2000-line god objects. Three places use this:

### 1. `MainWindow` (`ui/main_window.py`)

Inherits from `QMainWindow` plus **10 handler** and **5 builder mixins**. The
class itself only holds setup, status updates, panel coordination, and
pattern management.

| Builder mixins (`ui/builders/`) | Task |
|---|---|
| `ActionsBuilderMixin` | QAction definitions |
| `MenuBuilderMixin` | Menu bar |
| `ToolbarBuilderMixin` | Toolbar |
| `DockBuilderMixin` | Dock panels |
| `SignalsConnectorMixin` | Signal/slot wiring |

| Handler mixins (`ui/handlers/`) | Task |
|---|---|
| `FileHandlersMixin` | New/Open/Save/Import |
| `ExportHandlersMixin` | PDF/HTML/image/OXS/bundle export |
| `AutosaveHandlersMixin` | Autosave + recovery |
| `EditHandlersMixin` | Undo/redo, resize, rotate, flip |
| `ViewHandlersMixin` | Zoom, grid, symbols, minimap |
| `SelectionHandlersMixin` | Copy/cut/paste/fill |
| `UndoHandlersMixin` | Undo system integration |
| `PanelHandlersMixin` | Palette, color bar, layers, eyedropper |
| `ToolHandlersMixin` | Text tool, gradient tool |
| `MiscHandlersMixin` | Layers, recent files, templates, settings, about |

> Convention: mixins access the shared state of `MainWindow` via `self`
> (e.g. `self.current_pattern`). So that type checking and the IDE cooperate,
> the mixin methods declare `self: "MainWindow"` and import `MainWindow` only
> under `TYPE_CHECKING`.

### 2. The Canvas (`ui/canvas/`)

`CrossStitchCanvas` (`canvas.py`) is a `QWidget` and composes six mixins from
`ui/canvas/mixins/`:

- `CoordinatesMixin` — screen ↔ grid coordinate conversion
- `MirrorMixin` — mirror/symmetry mode
- `RenderingMixin` — drawing (paintEvent)
- `ZoomMixin` — zoom
- `MouseEventsMixin` — mouse/viewport events: pan, tool delegation, undo
  batching, wheel zoom
- `KeyboardEventsMixin` — keyboard events (tool keys, stitch navigation,
  arrow-key panning)
- `TabletGestureMixin` — pen tablet (pressure) and touch pinch gestures
- `PropertiesMixin` — properties/state

### 3. Tools (`ui/tools/`)

All drawing tools inherit from **`BaseTool`** (`base_tool.py`) and are
managed by the **`ToolManager`** (`tool_manager.py`). A tool overrides the
event hooks (`on_mouse_press/move/release`), `get_cursor()`, and optionally
`activate()/deactivate()`. The canvas forwards events to the active tool;
the tool returns changed cells `(x, y, color_index)`.

Tools: Pencil, Eraser, Fill, Line, Rect, Ellipse, Polygon, Gradient, Select,
Lasso Select, Move, Eyedropper, Text, Backstitch, Progress.

## Theme System (`ui/styles.py`)

PySticky supports dark/light with **live switching without a restart**.
Important to understand, because there are two mechanisms:

1. **Global app stylesheet** — `apply_theme_to_app(app)` sets a stylesheet on
   the `QApplication` that applies generically to all standard widgets
   (`QPushButton`, `QListWidget`, `QComboBox`, …). Most widgets need
   **nothing further** — they are automatically re-styled via this cascade
   when the theme changes.

2. **`_apply_theme()` method** — only widgets that set their **own** local
   stylesheet (which overrides the cascade) implement `_apply_theme()`.
   `reapply_theme(app)` re-sets the global stylesheet and then walks the
   widget tree via `_restyle_widget_tree()`, calling `_apply_theme()` on
   every widget that has this method.

> Rule of thumb: a panel needs `_apply_theme()` **only** if it calls
> `setStyleSheet(...)` itself. Otherwise the global cascade is enough.

Colors come from the `ThemeColors` dataclass (`DARK_THEME` / `LIGHT_THEME`).
The global `THEME` is patched across all modules on switch; in f-string
stylesheets, `THEME.xyz` therefore returns the current value at evaluation
time.

## Data Model & File Format

- **`Pattern`** (`core/pattern.py`) — the pattern: dimensions,
  `color_entries` (thread + symbol + stitch count), layer stack, metadata,
  backstitches.
- **`LayerStack` / `Layer`** (`core/layer.py`) — stitches per layer;
  `NO_STITCH` marks empty cells. Composite grid for the visible view.
- **`Thread` / `ThreadColor`** (`core/thread.py`) — yarn color (name, RGB,
  manufacturer, catalog number).
- **`.pxs`** — open, JSON-based project format. The current `FORMAT_VERSION`
  and the version history live in `core/file_io.py` (`save_pattern` /
  `load_pattern`).

## Import/Export (`io/`)

- **Export:** HTML, PDF (reportlab, optional), image (PNG/JPG/BMP), OXS,
  bundle (ZIP made of .pxs + html + png + pdf + yarn list).
- **Import:** OXS, PAT (PCStitch), XSD (Pattern Maker). The binary importers
  (`io/formats/`) share `_binary.py` (`decode_string`, `read_exact`).
- **Error convention:** exporters return `True` on success and **raise an
  exception with the cause on failure** (no silent `False`). The export
  worker or the respective handler shows the message in a dialog.

## Plugins (`plugins/`)

`plugins/api.py` defines the plugin interface and the loading;
`plugins/builtin/` contains bundled plugins (Border, Checkerboard,
Mirror-Horizontal). Each plugin has a manifest and a `run(pattern, ctx)`.

## Tests & Tooling

- **Tests:** `tests/`, run with `py -m pytest tests/ -x`. Qt tests use the
  `qtbot`/`qapp` fixtures (pytest-qt).
- **Lint/Format:** `ruff` (rules `E,F,W,I,N`, `line-length=100`). Deliberate
  exceptions are documented in `[tool.ruff.lint.per-file-ignores]` in
  `pyproject.toml`. Formatting via `ruff format` (replaces black).
- **Pre-commit:** `.pre-commit-config.yaml` (ruff + ruff-format). Enable
  with `pip install pre-commit && pre-commit install`.
- **Type checking:** mypy is configured in `[tool.mypy]`.

## Where do I start?

- New **tool**: look at `ui/tools/base_tool.py`, copy an existing tool,
  register it in `ToolManager`.
- New **export**: follow the pattern of the `io/` exporters (exception error
  convention!).
- New **panel**: create it in `ui/panels/`, hook it into `DockBuilderMixin`;
  `_apply_theme()` only if it has its own stylesheet.
- **Domain logic**: goes in `core/` — without a Qt dependency, so it stays
  well testable.
