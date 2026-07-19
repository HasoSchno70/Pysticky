# Changelog

*[Deutsch](CHANGELOG.md) | English*

All notable changes to PySticky are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
versioning based on [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.0.1] — 2026-07-19

### Added

- Windows installer (`PySticky-Setup.exe`) as an additional download option
  alongside the portable `.exe` — with Start Menu entry, optional desktop
  icon, and uninstaller

### Fixed

- Diamond Painting mode: the info-panel tooltip fell back to cross-stitch
  wording after the first stitch update instead of staying in Diamond mode
- Statistics dialog now hides the thread-usage/shopping-list tabs in
  Diamond Painting mode (skein math doesn't apply to diamonds); the
  progress tab says "diamonds placed" instead of "stitches stitched"
- "Stitch mode" (Ctrl+M) and "Generate tweed blend" are now disabled in
  Diamond Painting mode instead of staying clickable with no effect
- CI workflow: the test job's `GITHUB_TOKEN` had no restricted permissions
  (CodeQL finding, CWE-275) — now explicitly scoped to read-only

## [1.0.0] — 2026-07-18

### Fixed

- **Critical:** on large patterns (> 200×200 cells, e.g. wall-hanging
  designs), newly drawn stitches stayed invisible on the canvas — the
  chunk pixmap cache never knew a cell had changed and kept showing the
  old (mostly empty) rendered chunk
- Zooming on a large pattern afterwards showed wrongly scaled, shifted
  blocks — the same chunk cache never invalidated on zoom either; fixed
  by actually checking render parameters instead of just cell coordinates
- Aida fabric texture was missing entirely on large patterns (the chunk
  cache path drew empty cells as a flat color instead of the fabric look)
- Grid lines were practically invisible against the empty-cell background
  color (WCAG contrast ~1.0–1.4:1) — now automatically contrast-safe for
  any chosen color combination
- Default empty-cell color was accidentally dark navy instead of the
  intended cream fabric tone
- Drawing on a pattern with no added color created invisible stitches
  that still counted toward the stitch count (canvas stayed empty) — now
  rejected instead of silently producing wrong data
- "New" created a pattern with no color at all, so drawing immediately
  did nothing — a new pattern now automatically seeds the first color
  from the configured default palette
- Status bar contrast: text on several pills used the same accent color
  as the background tint and was barely readable
- Colors, General, Files, Tools, and Canvas settings tabs: 39 settings
  were dead UI (wrote to QSettings but were never read back) — now fully
  wired up. Settings with no feasible implementation (PDF quality, HTML
  inline CSS, selection add/subtract) were removed from the UI instead of
  being faked

## [0.9.0] — 2026-07-17

### Added

- Color tolerance (ΔE) for fill and "replace color" — now also replaces/
  fills similar, not just exactly matching, colors
- "Mystery mode" (Settings → Files → Export): prints pattern pages
  without colors (symbol + grid only) for surprise/blind-stitch kits
- "Repeat image import…" (File menu): reopens the import dialog pre-filled
  with the current pattern's source image, crop, and settings, so the
  import can be redone with tweaked values
- Replace-color dialog overhauled: suggestion tiles with the closest
  matching colors, a large original-➜-new preview, one-step auto-reduce
  of rare colors
- File logging (Settings → Diagnostics) — writes all errors to
  `~/.pysticky/logs` on request
- "Keyboard Shortcuts" settings tab is now actually wired up (was
  previously inert)
- Extended the Anchor palette by 76 previously-missing colors, then
  switched the whole palette to a verified source (stitchmate.app); did
  the same for DMC and Cosmo (Cosmo 91 → 542 colors)

### Changed

- Upgraded the color-distance metric everywhere from CIE76 to CIEDE2000
  (more accurate tolerance/similarity calculations)
- Diamond Painting now shows color symbols instead of DMC numbers
  everywhere (canvas, HTML/PDF export)
- Consolidated the Madeira palettes: removed the old 269-color file of
  unclear origin, the verified Mouliné palette (381 colors) is now the
  sole "Madeira" palette
- Dialog polish: removed duplicate title labels in 6 dialogs (the title
  is already in the window's title bar), unified inner spacing across
  ~23 dialogs
- Internally split the statistics dialog (1078 → 297 lines) and the
  image import dialog (1110 lines → 6 modules) — no visible change, just
  more maintainable

### Fixed

- **Critical:** 10 thread palettes (incl. Cosmo, Finca, Olympus, Valdani,
  Weeks Dye Works) never had a resolvable catalog number — importing an
  image into one of these palettes collapsed the entire pattern onto a
  single color
- Grid lines were barely visible against muted/gray thread colors (e.g.
  water/sky in photo imports) — contrast significantly increased
- Save crash on non-serializable state
- "Replace color" on large patterns: a multi-minute UI freeze from batch
  operations fixed (now ~0.25s instead of minutes)
- Ruler and start screen didn't update live on a theme switch
- Crash on color delete and mirror (nonexistent `clear_stitch`)
- Found and fixed two real keyboard shortcut collisions
  (`action_save_as`/`action_statistics`, among others)
- Statistics tables: color swatches on even rows were invisible

## [0.8.2] — 2026-07-15

### Fixed

- Heatmap dialog wouldn't open at all (loop variable `t` shadowed the
  `t()` translation function, causing a silent crash during setup)
- Image import dialog: the left settings column (especially the "Colors"
  section) looked cramped/hard to read at the fixed default size
- Windows autoscroll toast ("Scrolling disabled") when dragging in the
  image import crop preview (missing `event.accept()` on middle-click)
- Custom tooltip could cover a small widget's own number (e.g. a spin
  box) instead of appearing below it
- Statistics dialog: the tab bar (6 tabs incl. "Shopping List") got
  truncated on narrower screens; minimum width now fixed at 1200px, plus
  a bug fix in the auto-sizing calculation that could undercut the tab
  bar's own minimum width
- Screen eyedropper matched picked colors against all loaded thread
  palettes instead of only the currently selected one — could pull in
  colors from an unrelated manufacturer

### Changed

- Renamed "Multi-Hoop Planner" to "Split Across Frames" ("multi-hooping"
  is a machine-embroidery term, not standard in hand cross-stitch)

## [0.8.1] — 2026-07-15

### Added

- Yarn inventory list: the "In Pattern" tab now shows Needed/To Buy next
  to stock; "All Entries" allows manually adding a color (manufacturer
  picked from loaded palettes, color selectable directly instead of
  looking up the catalog number) and now also shows a color swatch
- Combined shopping list across multiple projects (yarn inventory)
- Community docs: SECURITY.md, CODE_OF_CONDUCT.md, CHANGELOG.md,
  issue/PR templates (German + English)
- Full English translations of all documentation files
- README: Screenshots section
- CI: version tags automatically publish a GitHub Release with the
  `.exe` attached

### Changed

- The top icon toolbar now scrolls on hover in narrow windows instead of
  showing Qt's default overflow menu (like the left tool palette)
- Settings dialog: auto-sizing now also accounts for the tab bar's own
  required width
- Moved the yarn inventory button into the toolbar (previously hidden
  only in the Edit menu)
- Layer panel buttons, custom tooltip instead of QToolTip, more visible
  mode switch

### Fixed

- Settings dialog theme bug, PDF/HTML export i18n gap
- Duplicate keyboard shortcuts (yarn inventory vs. pattern import,
  replace color vs. highlight color)
- ARCHITECTURE.md: corrected mixin count (six -> eight)

## [0.8.0] — 2026-07-15

First public snapshot. The list below is a rough summary — the full,
continuously updated feature overview is in the
[README](README.en.md#features).

### Added

- Grid-based pattern editor with 15 drawing tools, zoom/pan, snap-to-grid
- Stitch types: full, half, quarter, three-quarter, backstitch, French
  knot, beads, diamond-painting drills
- Layer system (visibility, lock, opacity, merging)
- 14 thread palettes (DMC, Anchor, Madeira, ...) + Mill Hill Beads +
  3 diamond-painting palettes, palette manager, tweed blends
  (multi-strand blended colors), manufacturer cross-reference
- Color tools: replace, swap, merge similar, harmonies, color-blindness
  simulation, symbol editor
- Native `.pxs` format with autosave + recovery
- Import: images (with quantization, dithering, confetti reduction),
  XSD/PAT/OXS, pattern library
- Export: HTML, PDF (A4/A3/A2/Letter), PNG/JPG/BMP, direct print, OXS
- Yarn inventory list with shopping list (also combined across multiple
  projects) and per-pattern demand calculation
- Undo/redo, statistics dialog, progress tracking
- Full internationalization (German/English)
- Dark/light theme with live switching
