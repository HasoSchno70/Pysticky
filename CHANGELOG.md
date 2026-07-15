# Changelog

Alle nennenswerten Änderungen an PySticky werden hier dokumentiert.

Format angelehnt an [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
Versionierung an [Semantic Versioning](https://semver.org/lang/de/) (solange
vor 1.0: `0.MINOR.PATCH`, Breaking Changes möglich innerhalb 0.x).

## [Unreleased]

## [0.8.0] — 2026-07-15

Erster öffentlicher Stand. Die folgende Liste ist eine grobe Zusammenfassung
— die vollständige, laufend aktuelle Feature-Übersicht steht in der
[README](README.md#features).

### Hinzugefügt

- Grid-basierter Muster-Editor mit 15 Zeichenwerkzeugen, Zoom/Pan, Snap-to-Grid
- Stichtypen: voll, halb, viertel, dreiviertel, Rückstich, Französischer
  Knoten, Perlen (Beads), Diamond-Painting-Drills
- Layer-System (Sichtbarkeit, Sperre, Deckkraft, Zusammenführen)
- 14 Garnpaletten (DMC, Anchor, Madeira, ...) + Mill Hill Beads +
  3 Diamond-Painting-Paletten, Paletten-Manager, Tweed-Blends
  (Multi-Strand-Mischfarben), Hersteller-Cross-Reference
- Farb-Werkzeuge: ersetzen, tauschen, zusammenführen, Harmonien,
  Farbblindheits-Simulation, Symbol-Editor
- Eigenes `.pxs`-Format mit Autosave + Recovery
- Import: Bilder (mit Quantisierung, Dithering, Confetti-Reduction),
  XSD/PAT/OXS, Muster-Bibliothek
- Export: HTML, PDF (A4/A3/A2/Letter), PNG/JPG/BMP, Direktdruck, OXS
- Garn-Vorratsliste mit Einkaufsliste (auch über mehrere Projekte
  kombiniert) und Bedarfsrechnung pro Muster
- Undo/Redo, Statistik-Dialog, Fortschritts-Tracking
- Vollständige Internationalisierung (Deutsch/Englisch)
- Dark/Light-Theme mit Live-Umschaltung
