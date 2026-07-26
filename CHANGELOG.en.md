# Changelog

*[Deutsch](CHANGELOG.md) | English*

All notable changes to PySticky are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
versioning based on [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.1.0] — 2026-07-26

The result of a multi-day, systematic clean-code-audit series (80+ rounds)
across the entire codebase — module by module, checked for data-loss risks,
crash candidates, and silently wrong behavior. No single headline feature,
but many small-to-medium fixes that together make undo, backstitches,
Diamond Painting mode, and import/export noticeably more robust.

### Changed

- Replace Color: new suggestion dialog shows the palette's most similar
  colors as tiles (with usage count) and offers automatic reduction of
  rarely-used colors ("confetti") onto the closest frequently-used color
- Mouse-wheel zoom now anchors on the cursor position instead of the
  canvas center
- Tweed-blend colors in the thread-usage tab, shopping list, and CSV
  export are now correctly resolved to their actual thread components
  instead of being counted as a single item
- CSV exports (thread list, statistics) now write a UTF-8 BOM so Excel
  displays special characters correctly

### Fixed

**Saving, Undo & Autosave**

- Saving a pattern with non-serializable state could crash the app instead
  of showing an error dialog; autosave and snapshot errors are now logged
  instead of being silently swallowed
- "Clear layer" completely bypassed the undo system; several tools
  (move selection, gradient, select/lasso) lost the stitch type on
  undo/move/rotate/mirror/paste
- Switching between cross-stitch and Diamond Painting mode didn't clear
  the undo history, which could lead to inconsistent restores; plugin undo
  (`LayerSnapshotCommand`) only remembered the layer index instead of a
  real object reference and could crash if a plugin changed the pattern
  size
- Autosave collision: multiple simultaneously running instances with a
  never-saved pattern overwrote each other via the same temp path; four
  further autosave/snapshot recovery bugs fixed; a corrupted autosave file
  crashed the app on startup instead of showing an error message; file
  autosave recovery was at times completely non-functional
- Bulk operations (replace color, fill, mirror) on large patterns could
  freeze the UI for minutes because panel updates fired per stitch instead
  of once per operation

**Layer Lock**

- Several tools (eraser, drawing tools, move selection) didn't consistently
  respect the layer lock and sometimes created no-op undo entries; the
  progress tool (mark stitches as done) was conversely blocked incorrectly
  by the lock, even though marking progress should remain possible on
  locked layers

**Backstitches**

- Backstitches were lost on rotate, mirror, crop, or resize; disappeared
  exactly at the pattern edge in the HTML export; were ignored by the
  pattern diff and the preview line-style display; still appeared in
  Diamond Painting mode where they don't belong
- "Replace color"/"swap colors" left the inherited half-stitch/bead stitch
  type attached to the wrong color; "remove color" orphaned backstitches;
  deleting always hit the oldest of several nearby lines instead of the
  one actually clicked
- XSD, OXS, and PAT import let backstitch coordinates and truncated or
  incomplete grid data through unchecked; OXS import silently swallowed
  broken references and float coordinates

**Diamond Painting mode**

- Several places still showed cross-stitch wording instead of Diamond
  Painting terms (time-estimate tab, shopping list, hoop-planner dialog,
  info-panel tooltip); the Diamond color list showed thread meters instead
  of drill counts
- Diamond drills were missing from the chunk-cache render path and in
  image export (rendered there as a flat square instead of a drill); the
  drill-rendering logic was duplicated in three places and is now
  consolidated

**Theme switching**

- Several UI elements kept their old look after a live theme switch: the
  toolbar, StatCard icons, the stitch-mode indicator, the Diamond Painting
  tooltip, and rows in the layer panel; the statistics tables didn't show
  color swatches at all in every second row

**Import & Export**

- Mystery mode still leaked the backstitch outline in the HTML export and
  was completely ignored by the bundle export
- PDF export could be crashed by certain user text; the color legend lost
  its column header row on subsequent pages with many colors; PDF
  protection checkboxes with no password set were ineffective, and the
  password wasn't trimmed; the cover page showed no stitching date
- Image export dropped backstitch outline lines entirely
- Drag & drop rejected the WebP, TIFF, and AVIF image formats at the
  window
- The pattern library let stale thumbnails and duplicate paths through

**Color management**

- Merging similar colors lost the half-/quarter-stitch and bead/diamond
  stamping of the affected stitches
- With more than 86 colors, image import assigned the "?" placeholder
  symbol to multiple colors instead of staying unique; importing a custom
  palette collapsed colors without a catalog number onto a single entry;
  the tweed-blend dialog created palette duplicates on repeated blending
- The shopping list counted stock against a duplicate thread multiple
  times

**Tools & Canvas**

- The gradient tool had an ineffective live preview, discarded the panel's
  starting color, and blocked entirely on a single-color palette
- The eyedropper occasionally picked up the wrong color with multiple
  layers; the mirror cursor preview could skip a mirrored cell depending
  on processing order; the polygon fill tool ran unbounded on clicks
  outside the pattern
- Drawing tools: the ellipse collapsed on very small drags, the line was
  direction-dependent, the rectangle produced duplicate edge points
- The zoom slider got stuck with individually configured cell sizes
- Drag-and-drop color swapping onto the color bar was practically never
  triggerable because the color swatch didn't accept a drag motion

**Dialogs & UI**

- The grid options dialog only affected the running session, never the
  saved settings; dock layout persistence was completely non-functional;
  saved keyboard shortcut overrides were applied without a collision
  check
- The new-project dialog let Diamond Painting preset / custom-template
  state linger between calls; cancelling no longer showed the welcome
  screen
- The image-import "Wizard Recall" (reopen import with different
  settings) lost pattern properties in the process
- The symbol editor ignored the configured symbol font
- Templates could be saved/renamed under duplicate names
- Very wide custom-tooltip text could slide completely off-screen
- "Recently opened" crashed on an entry that had since been deleted
- The heatmap dialog ignored resizing, normalized edge blocks incorrectly,
  and counted skipped (skip_stitching) colors into the evaluation; a
  hoop-planner dialog with a tiny hoop and high overlap froze completely
- The color list in the info panel truncated multi-character placeholder
  symbols at the cell edge and stopped following the correct color after
  deleting/reordering
- The statistics "coverage" card showed over 100% with multiple filled
  layers
- The previously dead backstitch options panel is now wired up and
  supports mirror mode as well

**Internationalization, accessibility & platform**

- Added 52 missing translations, plus several individual follow-ups
- Fixed three real accessibility bugs for keyboard/screen-reader use
- Numeric input fields showed a comma instead of a period without an
  explicit locale set; a tooltip in the version history showed hardcoded
  English weekday names
- On macOS, opening export folders silently failed because `xdg-open`
  doesn't exist there
- A hand-edited registry value with the wrong type crashed the settings
  tabs

**Robustness against corrupted files**

- Corrupted JSON/metadata values could crash the translation manager, the
  thread inventory, and the session timer; a malformed plugin manifest
  with the wrong character encoding did too
- Non-object entries in colors/layers/backstitches lists in a file are now
  caught instead of crashing the app
- Two previously silently swallowed save errors are now visible

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
