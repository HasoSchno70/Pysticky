# Changelog

*[Deutsch](CHANGELOG.md) | English*

All notable changes to PySticky are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
versioning based on [Semantic Versioning](https://semver.org/) (pre-1.0:
`0.MINOR.PATCH`, breaking changes possible within 0.x).

## [Unreleased]

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
