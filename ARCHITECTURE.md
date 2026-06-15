# Architektur

Dieses Dokument beschreibt den Aufbau von PySticky für neue Mitwirkende.
Es erklärt vor allem die wiederkehrenden Muster (Mixins, Theme-System,
Werkzeuge), damit man sich im Code schnell zurechtfindet.

## Überblick

PySticky ist eine **PySide6/Qt**-Desktop-App zum Entwerfen von
Kreuzstichmustern. Der Code ist in klare Schichten getrennt:

```
src/pysticky/
├── core/        Domänenlogik — KEIN Qt-UI (Pattern, Layer, Thread, Farbmathematik, .pxs-IO)
├── io/          Import/Export (HTML, PDF, Bild, Bundle, OXS, PAT, XSD)
├── ui/          Qt-UI (Hauptfenster, Canvas, Panels, Werkzeuge, Dialoge)
├── plugins/     Plugin-System (API + eingebaute Plugins)
├── resources/   Paletten (JSON), Icons, Stylesheets, Übersetzungen
├── utils/       Querschnitts-Helfer (Logging, Fehler)
├── config.py    APP_VERSION (einzige Versionsquelle) + UI-/Datei-Defaults
└── main.py      Einstiegspunkt: main()
```

**Schichtregel:** `core` kennt weder `io` noch `ui`. `io` darf `core` nutzen,
aber kein `ui`. `ui` darf alles nutzen. So bleibt die Domänenlogik testbar
ohne laufendes Qt.

## Einstiegspunkte

Alle Wege münden in `pysticky.main:main()`:

- `python run.py` — fügt `src/` zum Pfad hinzu (Entwicklung)
- `python -m pysticky` — über `__main__.py`
- `pysticky_main.py` — für den PyInstaller-Build
- `pysticky` (Konsolen-Skript aus `pyproject.toml`)

## Das Mixin-Muster

Große Qt-Klassen werden über **Mixins** in thematische Einheiten zerlegt,
statt zu 2000-Zeilen-Gott-Objekten zu wachsen. Drei Stellen nutzen das:

### 1. `MainWindow` (`ui/main_window.py`)

Erbt von `QMainWindow` plus **10 Handler-** und **5 Builder-Mixins**. Die
Klasse selbst hält nur Setup, Status-Updates, Panel-Koordination und
Pattern-Verwaltung.

| Builder-Mixins (`ui/builders/`) | Aufgabe |
|---|---|
| `ActionsBuilderMixin` | QAction-Definitionen |
| `MenuBuilderMixin` | Menüleiste |
| `ToolbarBuilderMixin` | Werkzeugleiste |
| `DockBuilderMixin` | Dock-Panels |
| `SignalsConnectorMixin` | Signal/Slot-Verdrahtung |

| Handler-Mixins (`ui/handlers/`) | Aufgabe |
|---|---|
| `FileHandlersMixin` | Neu/Öffnen/Speichern/Import |
| `ExportHandlersMixin` | PDF/HTML/Bild/OXS/Bundle-Export |
| `AutosaveHandlersMixin` | Autosave + Wiederherstellung |
| `EditHandlersMixin` | Undo/Redo, Resize, Rotate, Flip |
| `ViewHandlersMixin` | Zoom, Raster, Symbole, Minimap |
| `SelectionHandlersMixin` | Kopieren/Ausschneiden/Einfügen/Füllen |
| `UndoHandlersMixin` | Undo-System-Anbindung |
| `PanelHandlersMixin` | Palette, Farbleiste, Layer, Pipette |
| `ToolHandlersMixin` | Text-Werkzeug, Gradient-Werkzeug |
| `MiscHandlersMixin` | Layer, Recent Files, Templates, Settings, About |

> Konvention: Mixins greifen über `self` auf den geteilten Zustand der
> `MainWindow` zu (z. B. `self.current_pattern`). Damit Typprüfung und IDE
> mitspielen, deklarieren die Mixin-Methoden `self: "MainWindow"` und
> importieren `MainWindow` nur unter `TYPE_CHECKING`.

### 2. Der Canvas (`ui/canvas/`)

`CrossStitchCanvas` (`canvas.py`) ist ein `QWidget` und komponiert sechs
Mixins aus `ui/canvas/mixins/`:

- `CoordinatesMixin` — Umrechnung Bildschirm ↔ Raster
- `MirrorMixin` — Spiegel-/Symmetriemodus
- `RenderingMixin` — Zeichnen (paintEvent)
- `ZoomMixin` — Zoom
- `MouseEventsMixin` — Maus-/Viewport-Events: Pan, Tool-Delegation, Undo-Batching, Wheel-Zoom
- `KeyboardEventsMixin` — Tastatur-Events (Tool-Tasten, Sticken-Navigation, Pfeil-Pan)
- `TabletGestureMixin` — Stift-Tablet (Druck) und Touch-Pinch-Gesten
- `PropertiesMixin` — Properties/Zustand

### 3. Werkzeuge (`ui/tools/`)

Alle Zeichenwerkzeuge erben von **`BaseTool`** (`base_tool.py`) und werden
vom **`ToolManager`** (`tool_manager.py`) verwaltet. Ein Werkzeug überschreibt
die Event-Hooks (`on_mouse_press/move/release`), `get_cursor()` und optional
`activate()/deactivate()`. Der Canvas leitet Events an das aktive Werkzeug
weiter; das Werkzeug gibt geänderte Zellen `(x, y, color_index)` zurück.

Werkzeuge: Pencil, Eraser, Fill, Line, Rect, Ellipse, Polygon, Gradient,
Select, Lasso-Select, Move, Pipette, Text, Backstitch, Progress.

## Theme-System (`ui/styles.py`)

PySticky unterstützt Dark/Light mit **Live-Umschaltung ohne Neustart**. Wichtig
zu verstehen, weil es zwei Mechanismen gibt:

1. **Globales App-Stylesheet** — `apply_theme_to_app(app)` setzt ein
   Stylesheet auf die `QApplication`, das generisch für alle Standard-Widgets
   gilt (`QPushButton`, `QListWidget`, `QComboBox`, …). Die meisten Widgets
   brauchen **nichts weiter** — sie werden beim Theme-Wechsel automatisch über
   diese Kaskade neu gestylt.

2. **`_apply_theme()`-Methode** — nur Widgets, die ein **eigenes** lokales
   Stylesheet setzen (das die Kaskade überschreibt), implementieren
   `_apply_theme()`. `reapply_theme(app)` setzt das globale Stylesheet neu und
   läuft dann via `_restyle_widget_tree()` den Widget-Baum ab und ruft auf
   jedem Widget mit dieser Methode `_apply_theme()` auf.

> Faustregel: Ein Panel braucht `_apply_theme()` **nur**, wenn es selbst
> `setStyleSheet(...)` aufruft. Sonst genügt die globale Kaskade.

Farben kommen aus der `ThemeColors`-Dataclass (`DARK_THEME` / `LIGHT_THEME`).
Das globale `THEME` wird beim Wechsel über alle Module gepatcht; in f-String-
Stylesheets liefert `THEME.xyz` daher zur Auswertzeit den aktuellen Wert.

## Datenmodell & Dateiformat

- **`Pattern`** (`core/pattern.py`) — das Muster: Maße, `color_entries`
  (Faden + Symbol + Stichzahl), Layer-Stack, Metadaten, Backstitches.
- **`LayerStack` / `Layer`** (`core/layer.py`) — Stiche pro Layer; `NO_STITCH`
  markiert leere Zellen. Komposit-Grid für die sichtbare Ansicht.
- **`Thread` / `ThreadColor`** (`core/thread.py`) — Garnfarbe (Name, RGB,
  Hersteller, Katalognummer).
- **`.pxs`** — offenes, JSON-basiertes Projektformat. Die aktuelle
  `FORMAT_VERSION` und die Versionshistorie leben in `core/file_io.py`
  (`save_pattern` / `load_pattern`).

## Import/Export (`io/`)

- **Export:** HTML, PDF (reportlab, optional), Bild (PNG/JPG/BMP), OXS, Bundle
  (ZIP aus .pxs + html + png + pdf + Garnliste).
- **Import:** OXS, PAT (PCStitch), XSD (Pattern Maker). Die binären Importer
  (`io/formats/`) teilen sich `_binary.py` (`decode_string`, `read_exact`).
- **Fehler-Konvention:** Exporter geben bei Erfolg `True` zurück und **werfen
  bei Fehlschlag eine Exception mit Ursache** (kein stilles `False`). Der
  Export-Worker bzw. der jeweilige Handler zeigt die Meldung im Dialog.

## Plugins (`plugins/`)

`plugins/api.py` definiert die Plugin-Schnittstelle und das Laden;
`plugins/builtin/` enthält mitgelieferte Plugins (Border, Checkerboard,
Mirror-Horizontal). Jedes Plugin hat ein Manifest und eine `run(pattern, ctx)`.

## Tests & Tooling

- **Tests:** `tests/`, Ausführung mit `py -m pytest tests/ -x`. Qt-Tests nutzen
  die `qtbot`/`qapp`-Fixtures (pytest-qt).
- **Lint/Format:** `ruff` (Regeln `E,F,W,I,N`, `line-length=100`). Bewusste
  Ausnahmen stehen dokumentiert in `[tool.ruff.lint.per-file-ignores]` in
  `pyproject.toml`. Formatierung via `ruff format` (ersetzt black).
- **Pre-commit:** `.pre-commit-config.yaml` (ruff + ruff-format). Aktivieren
  mit `pip install pre-commit && pre-commit install`.
- **Typprüfung:** mypy ist in `[tool.mypy]` konfiguriert.

## Wo fange ich an?

- Neues **Werkzeug**: `ui/tools/base_tool.py` ansehen, ein bestehendes Werkzeug
  kopieren, im `ToolManager` registrieren.
- Neuer **Export**: an `io/`-Exportern orientieren (Exception-Fehlerkonvention!).
- Neues **Panel**: in `ui/panels/` anlegen, im `DockBuilderMixin` einhängen;
  `_apply_theme()` nur bei eigenem Stylesheet.
- **Domänenlogik**: nach `core/` — ohne Qt-Abhängigkeit, damit gut testbar.
