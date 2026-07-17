# PySticky — Kreuzstich-Software

*Deutsch | [English](README.en.md)*

Moderner Muster-Editor fuer Kreuzstich, in Python + PySide6.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.6+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Tests](https://img.shields.io/badge/Tests-798%20passing-brightgreen.svg)

## Screenshots

|                                       Editor                                        |                                    Garn-Vorratsliste                                     |                                   Muster-Statistiken                                    |
| :-----------------------------------------------------------------------------------: | :----------------------------------------------------------------------------------------: | :-----------------------------------------------------------------------------------------: |
| ![Editor](docs/screenshots/editor_main.png) | ![Garn-Vorratsliste](docs/screenshots/garn_vorrat.png) | ![Statistiken](docs/screenshots/statistik.png) |

*(Beispielmuster generiert, kein reales Foto — zeigt Farbquantisierung beim Bildimport.)*

## Features

### Muster-Editor
- Grid-basierter Editor mit Zoom (20–300 %) und Pan
- 15 Werkzeuge: Stift, Radierer, Fuellen, Pipette, Linie, Rechteck (gefuellt + Umriss), Ellipse (gefuellt + Umriss), Polygon (gefuellt + Umriss), Text, Rueckstich, Farbverlauf, Fortschrittsmarker, Auswahl (Rechteck + Lasso), Bewegen (Pan)
- Stichtypen: voller Kreuzstich, halbe Stiche (zwei Diagonal-Richtungen), Viertelstiche (alle vier Ecken), Dreiviertelstich, Franzoesischer Knoten, Rueckstich, **Perlen (Beads)**, **Diamond-Painting-Drills** — Bead und Diamond automatisch beim Zeichnen einer Bead-/DP-Farbe
- Auswahl-Werkzeuge: Rechteck + Lasso mit gemeinsamem Clipboard
- Auswahl-Operationen: Kopieren / Ausschneiden / Einfuegen / Loeschen / Fuellen / Drehen 90° / Spiegeln (per Menue oder Tastenkuerzel)
- Spiegelmodus beim Zeichnen (X / Y / beide Achsen, 2- / 4- / 8-fache Symmetrie)
- Magnetisches Raster (Snap-to-Grid)
- Fortschrittsmarkierung erledigter Stiche
- Drag&Drop von `.pxs`-Dateien und Bildern direkt auf das Fenster

### Layer-System
- Mehrere Ebenen mit Sicht­barkeit, Sperre, Deckkraft
- Ebenen umsortieren, vereinen, oder nur aktive zeichnen
- Andere Ebenen abdimmen fuer fokussiertes Arbeiten

### Farb- und Garnverwaltung
- 14 Garn­paletten (DMC, Anchor, Madeira, Cosmo, Olympus, Weeks Dye Works, Valdani, Venus, Finca, Sullivans, Riolis Gamma, Classic Colorworks, Gentle Art Sampler Threads) + **Mill Hill Beads** (Perlen, 100+ Codes) + **3 Diamond-Painting-Paletten** (DMC Diamond Painting 450 Codes, Diamond Art Club + Diamond Dotz als erweiterbare Skelette)
- **Tweed-Blends** (Multi-Strand-Blending): zwei Garne in einer Nadel kombinieren (z.B. 1 Strang DMC 310 + 1 Strang DMC 745 für Salt&Pepper-Effekte). Mischfarbe wird perzeptuell in CIE-Lab berechnet, beide Garnnummern erscheinen in der Legende.
- Farb-Bar mit Drag&Drop:
  - Drag von Palette auf die Farb-Bar fuegt eine Farbe hinzu
  - Drag eines Swatches auf einen anderen tauscht die beiden Farben (Quick-Color-Swap)
- Palette konvertieren (z.B. DMC → Anchor), Farb­paletten-Manager (sortieren, mergen, ungenutzte entfernen)
- Farbe ersetzen (A → B) und Farben tauschen (A ⇄ B) per Dialog mit Farbvorschau-Icons in den ComboBoxen
- Aehnliche Farben zusammenfuehren, Farb-Harmonien erzeugen
- Farb-Blindheits-Simulation (Protanopie / Deuteranopie / Tritanopie)
- Symbol-Editor pro Farbe mit Suchfunktion (Substring auf Zeichen, Unicode-Name, Codepoint `U+25CF` oder `25cf`)
- Symbole erweiterbar ueber `resources/symbols.txt`

### Datei + Export
- Eigenes `.pxs`-Format (JSON-basiert) mit Autosave + Recovery beim Start
- Recent-Files-Menue (`Datei → Zuletzt geoeffnet`)
- Pattern-Eigenschaften: Autor, Copyright, Stickdatum, freie Notizen — landen automatisch im HTML/PDF-Export-Deckblatt
- Import: Bilder (PNG/JPG/BMP/GIF/WebP/TIFF) mit Farb­quantisierung, Dithering und **Confetti-Reduction**, XSD/PAT/**OXS**-Formate, Muster-Bibliothek
- Export: HTML (mehrseitig, druckfertig), PDF (A4/A3/A2/Letter ueber reportlab), PNG/JPG/BMP, Direkt-Druck, **OXS (Open Cross Stitch XML)**
- **Hersteller-Cross-Reference in HTML/PDF-Legende**: zusaetzliche Spalten mit den jeweils naehesten Garn-Entsprechungen in anderen Hersteller-Paletten (Anchor, Madeira, …), Match per CIE-Lab Delta-E
- Export-Cache (`io/export_cache.py`): einmaliges Pre-Computing der Komposit-Grid-Daten pro Export-Lauf, ersetzt die Per-Pixel-Layer-Iteration in Cover/Preview/Pattern-Pages

#### OXS-Format (Open Cross Stitch XML)
Offener Austauschstandard, lesbar von Pattern Maker, MacStitch/WinStitch (Ursa Software), Stitch Fiddle und anderen kommerziellen Tools. PySticky kann OXS **lesen und schreiben** — alle Stichtypen (Voll-, Halb-, Viertel-, Dreiviertelstich, Rückstich, Französischer Knoten, Perle) überleben den Roundtrip. Hersteller+Catalog-Number aus OXS werden gegen die geladenen Paletten gematcht und zurück zu echten Threads aufgelöst.

Implementation: [io/formats/oxs_io.py](src/pysticky/io/formats/oxs_io.py).

#### Confetti-Reduction beim Bildimport
"Confetti" sind isolierte Einzelpixel oder Mini-Cluster im quantisierten Pattern, die beim Sticken unverhaeltnismaessig viele Garn-Wechsel erzeugen und kaum sichtbar sind. Der Slider "Confetti reduzieren" (1-10, Default 1 = aus) filtert sie heraus, indem kleine zusammenhängende Cluster der dominanten Nachbarfarbe zugeordnet werden. Praxis-Empfehlung: 2 für dezente, 3-5 für aggressive Reduktion bei foto-realistischen Mustern.

Algorithmus: Connected-Component-Labeling (4-Nachbarschaft) + iteratives Reassignen kleiner Cluster zur häufigsten Nachbarfarbe in 8-Nachbarschaft.

Implementation: [core/confetti_reduction.py](src/pysticky/core/confetti_reduction.py).

#### Cross-Reference-Spalten in der Legende
Im Settings-Dialog (Tab "Dateien" → Sektion "Export") können beliebige Hersteller-Paletten als Cross-Reference aktiviert werden. Die HTML- und PDF-Legende erhält dann zusaetzliche Spalten mit der jeweils naehesten Garn-Entsprechung. Match per CIE-Lab Delta-E (wahrnehmungsbasiert, nicht plain RGB). Ergebnisse werden gecached.

Implementation: [core/thread_cross_ref.py](src/pysticky/core/thread_cross_ref.py).

#### Perlen / Beads (v0.6)
Eigene Mill-Hill-Bead-Palette mit 100+ Codes (Glass Seed Beads, Petite Crystal, Antique etc.). Farben aus Bead-Paletten werden automatisch erkannt (`ColorEntry.is_bead`) — beim Zeichnen wird der Stich-Type auf BEAD gesetzt, ohne dass ein separates Werkzeug nötig ist. In der HTML/PDF-Legende erscheinen Perlen in einer eigenen Sektion ("Perlen (Beads)"), und Bead-Farben werden NICHT als Garn-Strang-Bedarf gerechnet.

Implementation: Palette in [resources/palettes/Mill_Hill_Beads_Farben.json](src/pysticky/resources/palettes/Mill_Hill_Beads_Farben.json), Datenmodell in [core/pattern.py](src/pysticky/core/pattern.py) (`ColorEntry.is_bead`), automatisches Stitch-Type-Mapping in `Pattern.set_stitch`.

#### Diamond Painting (v0.8)
PySticky kann jetzt auch **Diamond-Painting-Vorlagen** erzeugen — ein vollwertiger Modus, kein bloßes Render-Overlay.

- **Pattern-Modus** (`Pattern.mode ∈ {"stitch", "diamond"}`): Jedes Muster trägt seinen Modus selbst, persistiert in `.pxs`. Beim Öffnen passt sich die ganze UI automatisch an — Mode-Switch-Button, Info-Panel-Labels, Stoff-/Drill-Auswahl, verfügbare Werkzeuge. Ältere `.pxs`-Dateien ohne Mode-Feld werden als Stick-Modus geladen (rückwärtskompatibel).
- **Mode-Switch in der Toolbar** (`Modus: 💎 Diamond` / `🧵 Kreuzstich`): Prominenter Toggle-Button. Der Text zeigt immer, *wohin* du wechselst. Plus Menü `Ansicht → Diamond-Painting-Ansicht` und Shortcut `Ctrl+D` — alle drei Wege bleiben synchron.
- **Auto-Palette beim Wechsel**: Wechsel zu Diamond lädt die `DMC Diamond Painting`-Palette und merkt sich die vorher aktive Garn-Palette. Beim Zurückwechseln springt das Palette-Panel auf die gemerkte Palette zurück.
- **UI passt sich modus-spezifisch an**: Im DP-Modus zeigt das Info-Panel „Drills" statt „Stiche", „Klebezeit" statt „Stickzeit" (~3s/Drill statt ~20s/Stich), „Drill-Bedarf" mit 10% Reserve statt Garn-Meter, und Drill-Raster-Auswahl (2.5/2.8/3.0 mm) statt Aida-Count. Stick-spezifische Werkzeuge (Rückstich, Französischer Knoten, Halb-/Viertel-/Dreiviertelstich) werden im DP-Modus ausgegraut.
- **Drei Diamond-Painting-Paletten**: `DMC_Diamond_Painting_Farben.json` (450 offizielle Codes), plus Skelette für `Diamond_Art_Club_Diamond_Painting_Farben.json` und `Diamond_Dotz_Diamond_Painting_Farben.json` (~40 Sample-Codes je, da Hersteller keine RGB-Listen veröffentlichen — siehe [resources/palettes/DIAMOND_PALETTES.md](src/pysticky/resources/palettes/DIAMOND_PALETTES.md) zum Erweitern). Paint With Diamonds / Dreamer Designs verwenden DMC-Codes → nutzen direkt die DMC-DP-Palette.
- **Automatische Stitch-Type-Erkennung**: Paletten mit `Diamond` im Dateinamen werden über `ThreadPalette.is_diamond=True` gekennzeichnet. Farben aus DP-Paletten setzen beim Zeichnen automatisch den `DIAMOND`-Stich-Type, analog zu Beads.
- **Drill-Rendering**: Facettierte Drills mit Glanzlicht oben und Schatten unten — die typische DP-Optik. Symbole werden durch **DMC-Nummern** ersetzt, die Aida-Stoff-Textur durch einen DP-Klebegrund.

Implementation: `Pattern.mode` in [core/pattern.py](src/pysticky/core/pattern.py), `StitchType.DIAMOND = 11` in [core/stitch.py](src/pysticky/core/stitch.py), `ThreadPalette.is_diamond` in [core/palette.py](src/pysticky/core/palette.py), Mode-Switch-Button in [ui/builders/mw_toolbar_mixin.py](src/pysticky/ui/builders/mw_toolbar_mixin.py), zentraler Modus-Sync in [ui/handlers/view_handlers.py](src/pysticky/ui/handlers/view_handlers.py) (`_apply_pattern_mode`), Info-Panel-Labels in [ui/panels/info_panel.py](src/pysticky/ui/panels/info_panel.py) (`set_mode`), Drill-Renderer in [ui/canvas/mixins/rendering_mixin.py](src/pysticky/ui/canvas/mixins/rendering_mixin.py). Tests in [tests/test_diamond.py](tests/test_diamond.py) (25 Tests).

#### Tweed-Blending / Multi-Strand-Garn (v0.6)
Profi-Kreuzstich kombiniert oft zwei Garne in einer Nadel — z.B. 1 Strang DMC 310 + 1 Strang DMC 745 für einen Salt&Pepper-Effekt. Der Menüpunkt `Bearbeiten → Palette → Tweed-Blend erzeugen…` öffnet einen Dialog mit Vorschau, der zwei Threads aus den geladenen Paletten kombiniert (1–6 Stränge pro Komponente einstellbar). Mischfarbe wird perzeptuell im CIE-Lab-Raum berechnet (kein Plain-RGB-Average). In der Legende erscheinen beide Garnnummern (z.B. "DMC 310 + DMC 745 (1+1)"). Blends überleben den .pxs-Roundtrip; im OXS-Export werden die Komponenten als Custom-Attribute mitgegeben.

Implementation: [core/thread.py](src/pysticky/core/thread.py) (`Thread.blend`, `_blend_colors_lab`, `_rgb_to_lab_single`/`_lab_to_rgb_single`), Dialog in [ui/dialogs/blend_threads_dialog.py](src/pysticky/ui/dialogs/blend_threads_dialog.py).

#### Working-Chart-Pages mit Overlap (v0.6)
Konfigurierbar in Settings → Dateien → Export → "Seiten-Overlap" (0-20 Stiche). Jede HTML/PDF-Seite zeigt zusätzlich die ersten N Stiche der Nachbarseite (rechts/unten), visuell als Overlap-Zone markiert. Erleichtert das Aneinanderlegen ausgedruckter Seiten. Plus Mini-Seiten-Index (kleine Grid-Übersicht aller Seiten mit der aktuellen Seite hervorgehoben) und Pfeil-Marker zu den Nachbarseiten.

Implementation: [io/html_export_pages.py](src/pysticky/io/html_export_pages.py) (`_build_page_mini_index`, `_build_page_neighbor_markers`), Overlap-Berechnung pro Seite mit `core_end_x + overlap`.

#### Internationalisierung (v0.7)
PySticky unterstützt jetzt **mehrsprachige Oberflächen**. Mitgeliefert: Deutsch (Default) und Englisch (~150 übersetzte Strings für Menüs, Toolbar, Statusbar, häufige Dialoge). Sprache umstellbar in `Einstellungen → Allgemein → Sprache` (Auto / Deutsch / English).

Architektur: JSON-Dictionary-basiert mit Identity-Fallback (Default-Sprache = Source-Strings im Code = deutsch). Fehlende Übersetzungen liefern den deutschen Original-String, kein Crash. Weitere Sprachen können einfach durch eine neue `<langcode>.json` in `resources/i18n/` hinzugefügt werden — der Loader findet sie automatisch.

Implementation: [core/i18n.py](src/pysticky/core/i18n.py) (`TranslationManager`, `t()`, `set_language()`), Dictionaries in [resources/i18n/](src/pysticky/resources/i18n/).

Hinweis: Migration der UI-Strings ist iterativ. Kern-Menüs und kritische Dialoge sind übersetzt; tiefere Dialoge laufen noch in deutsch. Wer eine weitere Sprache will, kopiert `en.json` → `<code>.json` und übersetzt die Values.

#### Plugin-API (v0.7)
**Eigene Python-Skripte können das Pattern manipulieren**. Plugins liegen in eigenen Verzeichnissen mit `manifest.json` + Python-Modul und werden automatisch entdeckt aus:

1. `src/pysticky/plugins/builtin/` (mitgeliefert)
2. `~/.pysticky/plugins/` (User-installiert)

Plugin-Signatur:
```python
def run(pattern, ctx):
    width = ctx.prompt_int("Wie breit?", default=10, minimum=1, maximum=100)
    if width is None:  # User hat abgebrochen
        return
    # ... Pattern via pattern.set_stitch(), pattern.add_color() etc. manipulieren ...
    ctx.show_message(f"Fertig — {width} Stiche gesetzt.")
```

Mitgelieferte Beispiel-Plugins (siehe [src/pysticky/plugins/builtin/](src/pysticky/plugins/builtin/)):
- **Rahmen generieren** — zeichnet einen rechteckigen Rahmen mit konfigurierbarem Abstand + Linienstärke
- **Schachbrett füllen** — zweifarbiges Schachbrett mit konfigurierbarer Feldgröße
- **Horizontal spiegeln** — kopiert die linke Pattern-Hälfte gespiegelt auf die rechte (für symmetrische Motive)

Aufruf: `Werkzeuge → Plugins…`. Implementation: [plugins/api.py](src/pysticky/plugins/api.py) (Discovery, Manifest, run_plugin), Dialog in [ui/dialogs/plugin_dialog.py](src/pysticky/ui/dialogs/plugin_dialog.py).

#### PDF-Schutz (v0.7)
Beim PDF-Export erscheint ein neuer Schutz-Dialog mit drei Optionen:

- **Passwort** — verschlüsselt das PDF mit AES-128 (reportlab StandardEncryption). Ohne Passwort lässt sich das PDF nicht öffnen.
- **Wasserzeichen** — Text wird groß diagonal mit 35 % Transparenz auf jede Seite gezeichnet ("ENTWURF", "VORSCHAU", Designer-Name, …).
- **Drucken erlauben / Kopieren erlauben** — Checkboxes, die in die PDF-Permissions geschrieben werden (von Adobe Reader und den meisten Viewern respektiert).

Implementation: [io/pdf_export.py](src/pysticky/io/pdf_export.py) (`StandardEncryption`-Integration, `_draw_footer`-Hook für Watermark), Dialog [ui/dialogs/pdf_protect_dialog.py](src/pysticky/ui/dialogs/pdf_protect_dialog.py).

#### Tablet- und Stift-Druck (v0.8)
PySticky reagiert jetzt auf Stift-Druck (Wacom, Surface Pen, iPad mit Apple Pencil). Bei aktiviertem Stift moduliert der Druck die Brush-Größe des Pencil-Tools — leichter Druck = 1 Stich, voller Druck = bis zu N Stiche im Kreis (konfigurierbar). Maus-Eingabe bleibt unverändert: 1 Klick = 1 Stich.

Konfigurierbar in `Einstellungen → Werkzeuge → Tablet & Stift`: "Druck nutzen" und "Max. Brush-Groesse" (1–20).

Implementation: `tabletEvent`-Handler in [ui/canvas/mixins/events_mixin.py](src/pysticky/ui/canvas/mixins/events_mixin.py) speichert `_tablet_pressure`, das Pencil-Tool ([ui/tools/pencil_tool.py](src/pysticky/ui/tools/pencil_tool.py)) berechnet daraus den Brush-Radius.

#### Touch-Gesten / Pinch-Zoom (v0.8)
Für Touchscreens (Surface, iPad) gibt es Pinch-Zoom auf dem Canvas. Standardmäßig **aus**, weil Windows auf manchen Geräten einen "Tablet"-Toast beim langen Drag zeigt, wenn Touch-Events akzeptiert werden. Aktivierbar in `Einstellungen → Werkzeuge → Tablet & Stift → Touch-Gesten`.

Implementation: `grabGesture(PinchGesture)` + `event()`-Override im Canvas, `_handle_gesture` mit Schwellwert-Detection für Zoom-Trigger.

#### Screen-EyeDropper (v0.8)
`Werkzeuge → Farbe vom Bildschirm picken…` öffnet ein Vollbild-Overlay mit dem aktuellen Screenshot. Klick auf eine Stelle pickt die Pixelfarbe; PySticky sucht automatisch die naheste Garn-Entsprechung in den geladenen Paletten (CIE-Lab Delta-E, Bead-Paletten ausgeschlossen) und fügt sie zur Pattern-Palette hinzu.

Praktisch für: Farben aus Referenzbildern im Browser, Foto-Editor oder anderem Tool übernehmen.

Implementation: [ui/dialogs/screen_eyedropper_dialog.py](src/pysticky/ui/dialogs/screen_eyedropper_dialog.py) mit testbaren Top-Level-Funktionen `pick_color_at` und `find_nearest_thread`.

#### Snapshot-Diff (v0.8)
Im Versionen-Dialog (`Datei → Versionen…`) gibt es jetzt einen "⇄ Mit aktuellem vergleichen"-Button. Öffnet einen Drei-Spalten-Vergleich: Alt | Neu | Diff-Overlay mit Stich-Änderungen farbig markiert (grün = hinzugefügt, rot = entfernt, gelb = geändert). Statistik oben: X+ Y- Z~.

Implementation: [core/pattern_diff.py](src/pysticky/core/pattern_diff.py) (`compute_diff`, `DiffStats`, `DiffResult` — UI-frei, headless testbar), Dialog [ui/dialogs/pattern_diff_dialog.py](src/pysticky/ui/dialogs/pattern_diff_dialog.py).

#### Smart-Resize (v0.8)
Im Resize-Dialog gibt es eine Checkbox "Stiche neu verteilen (Smart-Resize)". Aktiv: das Pattern wird wie ein Pixelbild bilinear skaliert, Stiche neu auf die neue Zellgröße verteilt — ideal beim Hochskalieren (50×50 → 100×100 mit den Stichen voll genutzt statt 75 % leere Zellen). Aus: klassisches Croppen/Padding wie bisher.

Stitch-Type-Grid wird mit nearest-neighbor übernommen, Backstitches werden proportional skaliert.

Implementation: [core/smart_resize.py](src/pysticky/core/smart_resize.py).

### Visualisierung
- **Stoff-Vorschau-Panel**: realistische Darstellung des fertigen Werkstuecks auf gewaehltem Stoff (Aida 11–32, Evenweave, Leinen) und Stoff-Farbe
  - Volle Kreuzstiche als gezeichnete X-Form
  - Halbe / Viertel / Dreiviertel-Stiche als echte diagonale Garn-Linien
  - Franzoesische Knoten als kleine glaenzende Kugeln
  - Rueckstiche, Stofftextur, Zoom
- **Heatmap-Dialog** (`Bearbeiten → Heatmap…`): Pattern als Heatmap visualisieren, Achsen Stichdichte oder Farbenvielfalt, konfigurierbare Block-Groesse
- **Pattern-Vorschau** als separater Dialog
- **Tile-Vorschau** fuer wiederholende Muster
- **Minimap** mit Viewport-Anzeige

### Workflow-Werkzeuge
- Statistik-Dialog: Stichzahl pro Farbe, Garnverbrauch (Aida 11–32), Zeitschaetzung, Kit-Kosten-Rechner
- Stickpfad-Optimierung: berechnet effiziente Reihenfolge der Stiche pro Farbe
- Muster-Bibliothek mit Thumbnails
- Projekt-Templates (Lesezeichen, Deckchen, Kissen, Weihnachten, …)
- Eigenschaften-Dialog: Pattern-Metadata (Autor, Copyright, Stickdatum, Notizen) — Notizen erscheinen auch im Export-Deckblatt

### Performance
- Chunk-basiertes Canvas-Caching fuer grosse Muster
- Level-of-Detail (LOD): Skip von Symbolen/Grid bei kleinem Zoom
- Auto-Aktivierung der Performance-Optimierungen ab Schwellwert
- Export-Cache fuer HTML/PDF: vorberechnete numpy-Arrays statt Per-Zellen-Layer-Walks
- Details: siehe [`PERFORMANCE_OPTIMIZATIONS.md`](PERFORMANCE_OPTIMIZATIONS.md) und [`src/pysticky/ui/canvas/README.md`](src/pysticky/ui/canvas/README.md)

### UI
- **Welcome-Screen** beim Start mit Quick-Start-Aktionen (Neu / Oeffnen / Aus Bild) und Liste der zuletzt geoeffneten Dateien
- **Dark + Light Theme**, live umschaltbar in den Einstellungen
- **Farblich gruppierte Toolbar**: Datei (gruen), Bearbeiten (orange), Zoom (blau), Ansicht (lila), Symmetrie (rot), Stich (gelb) — visuell trennbare Sektionen mit farbigen Trennlinien
- **Statusleiste mit Farb-Pills**: Tool, Stichtyp, Position, Farbe-unter-Maus, Ebene, Groesse, Stichzahl, Undo — jeweils mit eigener Akzent-Farbe und fester Mindestbreite (kein Flackern beim Mausbewegen)
- Andockbare Panels: Palette, Farbleiste, Ebenen, Info, Minimap, Tile-Vorschau, Stoff-Vorschau, Fortschritt
- Lineale + klickbare Navigation, Zoom-Slider in der Statusleiste
- Konfigurierbare Einstellungen (6 Tabs: Allgemein / Canvas / Werkzeuge / Farben / Dateien / Tastenkuerzel)

## Installation

### Fertige .exe (Windows)

Fertig gebaute Windows-`.exe` gibt's auf der
[Releases-Seite](https://github.com/HasoSchno70/Pysticky/releases) —
herunterladen und direkt starten, keine Installation von Python nötig.

### Aus dem Quellcode

```bash
git clone https://github.com/HasoSchno70/Pysticky.git
cd Pysticky

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
python run.py
```

Optional fuer Entwickler/Build:
```bash
pip install -e ".[dev]"     # pytest, pytest-qt, black, ruff
pip install -e ".[build]"   # pyinstaller
```

Aufbau des Codes (Schichten, Mixin-Muster, Theme-System, Werkzeuge):
siehe [ARCHITECTURE.md](ARCHITECTURE.md). Build-Anleitung in [BUILD.md](BUILD.md).

## Bedienung

### Maus
| Aktion | Funktion |
|--------|----------|
| Linke Taste | Werkzeug-Aktion (Stich setzen, Auswahl ziehen, …) |
| Rechte Taste | Stich loeschen (im Zeichen-Tool); Kontextmenue auf Farb-Bar |
| Mittlere Taste (halten) | Ansicht verschieben |
| Move-Tool + Linksklick | Ansicht verschieben (alternativ) |
| Mausrad | Zoom |
| Drag auf Farb-Bar | Farbe hinzufuegen (von Palette) oder tauschen (von Swatch) |

### Globale Tastenkuerzel
Alle Tastenkuerzel sind unter Einstellungen -> Tastenkuerzel individuell
anpassbar (Doppelklick auf einen Eintrag).

| Kuerzel | Funktion |
|---------|----------|
| `Ctrl+N` / `Ctrl+O` / `Ctrl+S` | Neu / Oeffnen / Speichern |
| `Ctrl+Shift+S` | Speichern unter |
| `Ctrl+Alt+P` | Eigenschaften (Autor, Notizen, Stickdatum) |
| `Ctrl+Alt+V` | Versionen |
| `Ctrl+I` / `Ctrl+Alt+I` | Bild importieren / XSD-PAT importieren |
| `Ctrl+L` | Muster-Bibliothek |
| `Ctrl+E` / `Ctrl+Shift+E` / `Ctrl+Alt+E` | Export HTML / PDF / Bild |
| `Ctrl+P` | Drucken |
| `Ctrl+Z` / `Ctrl+Y` | Rueckgaengig / Wiederherstellen |
| `Ctrl+R` | Farbe ersetzen |
| `Ctrl+H` | Aktive Farbe hervorheben |
| `Ctrl+Shift+T` | Farben tauschen |
| `Ctrl+Shift+P` | Farbpalette verwalten |
| `Ctrl+Shift+H` | Farb-Harmonien |
| `Ctrl+Shift+C` | Auto-Zuschneiden |
| `Ctrl+Shift+M` | Aehnliche Farben zusammenfuehren |
| `Ctrl+Shift+K` | Palette konvertieren |
| `Ctrl+Shift+G` | Statistiken + Garnverbrauch |
| `Ctrl+Shift+I` | Garn-Vorrat |
| `Ctrl+M` | Sticken-Modus |
| `Ctrl+Shift+O` | Stickpfad-Optimierung |
| `Ctrl+D` | Diamond-Ansicht |
| `F5` | Vorlagen-Vorschau |
| `Ctrl+Shift+N` | Neue Ebene |
| `Ctrl+,` | Einstellungen |
| `Ctrl++` / `Ctrl+-` / `Ctrl+0` / `Ctrl+1` | Zoom +/- / Einpassen / 100 % |
| Pfeiltasten | Canvas verschieben |
| `F1` | Tastenkuerzel-Uebersicht |

### Werkzeug-Shortcuts
`P` Stift · `E` Radierer · `F` Fuellen · `I` Pipette · `L` Linie · `R` Rechteck · `O` Ellipse · `G` Polygon · `T` Text · `B` Rueckstich · `D` Farbverlauf · `K` Fortschritt · `S` Auswahl (Rechteck/Lasso) · `M` Bewegen

Bei den Form-Werkzeugen (Rechteck/Ellipse/Polygon) und der Auswahl schaltet ein zweiter Klick auf den bereits aktiven Werkzeug-Button zwischen den beiden Varianten um (z. B. Umriss/Gefuellt, Rechteck/Lasso) — nicht ueber eine eigene Tastenkombination.

### Auswahl
| Kuerzel | Funktion |
|---------|----------|
| `Ctrl+C` / `Ctrl+X` / `Ctrl+V` | Kopieren / Ausschneiden / Einfuegen (auch ueber Tool-Grenzen, schaltet bei Paste auto auf Select) |
| `Entf` | Stiche in Auswahl loeschen |
| `F` | Auswahl mit aktueller Farbe fuellen (nur wenn Select-Tool aktiv) |
| `R` / `Shift+R` | Auswahl drehen 90° rechts / links (nur Select-Tool) |
| `H` / `V` | Auswahl horizontal / vertikal spiegeln (nur Select-Tool) |
| `Esc` | Auswahl aufheben |

## Projektstruktur

```
src/pysticky/
├── app.py                     # PySticky-App-Klasse
├── main.py                    # Entry-Point (gui-script)
├── __main__.py                # `py -m pysticky`
├── config.py                  # Klassen-Konfiguration (CANVAS_CONFIG, UI_CONFIG, …)
├── core/                      # Domain-Modell, keine UI-Abhaengigkeiten
│   ├── pattern.py             # Pattern + ColorEntry + metadata
│   ├── layer.py               # LayerStack mit numpy-basierten Grids
│   ├── stitch.py / stitch_shapes.py   # Stitch-Typen, Polygon-Eckpunkte
│   ├── thread.py              # Thread + ThreadColor + Tweed-Blend (Lab-Mix)
│   ├── palette.py             # Garn-/Bead-Paletten (is_beads-Flag)
│   ├── backstitch_manager.py
│   ├── undo.py                # Command-Pattern + Batches
│   ├── file_io.py             # .pxs-Roundtrip
│   ├── image_import.py        # Bild → Pattern mit Quantisierung/Dithering
│   ├── confetti_reduction.py  # Connected-Components-Filter fuer Mini-Cluster
│   ├── thread_cross_ref.py    # CIE-Lab Lookup Hersteller-Aequivalent
│   ├── i18n.py                # i18n: TranslationManager + t()
│   ├── pattern_diff.py        # Snapshot-Vergleich (added/removed/changed)
│   ├── smart_resize.py        # Bilineares Resampling fuer Pattern-Resize
│   ├── color_blindness.py     # Simulation
│   ├── stitch_path_optimizer.py
│   └── constants.py
├── plugins/                   # Plugin-System
│   ├── api.py                 # Plugin, PluginContext, discover, run
│   └── builtin/               # Mitgelieferte Demo-Plugins
│       ├── border/            # Rahmen generieren
│       ├── checkerboard/      # Schachbrett fuellen
│       └── mirror_horizontal/ # Linke Haelfte spiegeln
├── io/                        # Export / Import
│   ├── export_common.py       # gemeinsame Pixel-Lookup-Helpers
│   ├── export_cache.py        # numpy-Komposit-Grid-Cache fuer Export
│   ├── html_export*.py
│   ├── pdf_export*.py
│   ├── image_export.py
│   └── formats/               # XSD-/PAT-Importer + OXS Read/Write
├── ui/
│   ├── main_window.py
│   ├── styles.py              # Dark + Light Theme
│   ├── workspace_profiles.py
│   ├── builders/              # MainWindow-Mixins: actions/docks/menus/signals/toolbar
│   ├── handlers/              # MainWindow-Mixins: file/export/autosave/edit/view/
│   │                          #   selection/undo/panel/tool/misc
│   ├── canvas/                # CrossStitchCanvas + OptimizedCanvas + Mixins
│   ├── tools/                 # 15 Zeichenwerkzeuge + ToolManager
│   ├── dialogs/               # Statistik, Settings, Import, Library, Heatmap,
│   │                          #   Swap, Pattern-Properties, Symbol-Editor, …
│   ├── panels/                # Palette, Layer, Info, Minimap, Progress,
│   │                          #   Tile-Preview, Fabric-Preview, …
│   ├── widgets/               # ColorBar, Ruler, ZoomSlider, WelcomeWidget, …
│   ├── workers/               # QThread-Worker (Stickpfad, Export)
│   └── rendering/             # Preview-Render-Engine
└── resources/
    ├── palettes/              # 14 JSON Garn-Paletten + Mill Hill Beads
    ├── i18n/                  # Sprach-Dictionaries (de.json, en.json)
    ├── styles/                # QSS (dark.qss)
    ├── symbols.txt            # 86 Standard-Symbole (erweiterbar)
    └── icons/                 # App-Icons
tests/
├── conftest.py + 36+ test_*.py # 787 Tests, alle gruen
```

## Entwicklung

### Tests

```bash
pytest tests/                            # 787 Tests in ~11 s
pytest tests/ --cov=src/pysticky         # mit Coverage-Report
```

### Code-Stil

```bash
black src/                  # Formatierung (line-length 100)
ruff check src/             # Linting (E, F, W, I, N)
```

### Architektur-Notizen

- Strikte Trennung `core/` (rein Python) und `ui/` (PySide6) — `core/` kann ohne Qt importiert werden
- Modul-Konfiguration in `config.py` (Dataclasses) leitet von `core/constants.py` ab — Single Source of Truth fuer Werte
- MainWindow ist via Mixins aufgeteilt (Handler + Builder) — jede Datei mit fokussierter Verantwortung
- Canvas nutzt automatisch eine `OptimizedCrossStitchCanvas` mit Chunk-Caching fuer grosse Muster
- Theme-System: `styles.py` exportiert `THEME` (live patchbar via `set_theme()`); Theme-Wechsel propagiert ueber `_apply_theme()`-Methoden auf den Widgets
- Stitch-Typen: einheitliche Polygon-Definitionen in `core/stitch_shapes.py`, benutzt von Canvas, Fabric-Preview, HTML- und PDF-Export

## Lizenz

MIT — siehe [LICENSE](LICENSE).

## Beitragen

1. Fork erstellen
2. Branch (`git checkout -b feature/<name>`)
3. Commit mit aussagekraeftiger Message
4. Tests laufen lassen (`pytest tests/`)
5. Pull Request

Mehr Details in [CONTRIBUTING.md](CONTRIBUTING.md). Für alle Mitwirkenden
gilt unser [Verhaltenskodex](CODE_OF_CONDUCT.md). Sicherheitslücken bitte
gemäß [SECURITY.md](SECURITY.md) melden. Änderungen an PySticky stehen im
[CHANGELOG](CHANGELOG.md).
