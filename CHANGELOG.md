# Changelog

*Deutsch | [English](CHANGELOG.en.md)*

Alle nennenswerten Änderungen an PySticky werden hier dokumentiert.

Format angelehnt an [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
Versionierung an [Semantic Versioning](https://semver.org/lang/de/) (solange
vor 1.0: `0.MINOR.PATCH`, Breaking Changes möglich innerhalb 0.x).

## [Unreleased]

## [0.8.1] — 2026-07-15

### Hinzugefügt

- Garn-Vorratsliste: "Im Muster"-Tab zeigt jetzt Benötigt/Zu-kaufen neben
  dem Bestand; "Alle Einträge" erlaubt manuelles Hinzufügen einer Farbe
  (Hersteller-Auswahl aus geladenen Paletten, Farbe direkt wählbar statt
  Katalognummer nachzuschlagen) und zeigt jetzt ebenfalls ein Farbquadrat
- Kombinierte Einkaufsliste über mehrere Projekte hinweg (Garn-Vorrat)
- Community-Docs: SECURITY.md, CODE_OF_CONDUCT.md, CHANGELOG.md,
  Issue-/PR-Templates (Deutsch + Englisch)
- Vollständige englische Übersetzungen aller Doku-Dateien
- README: Screenshots-Sektion
- CI: Versions-Tags veröffentlichen automatisch ein GitHub-Release mit
  angehängter `.exe`

### Geändert

- Obere Icon-Leiste scrollt bei schmalen Fenstern per Hover statt Qt's
  Standard-Überlaufmenü zu zeigen (wie die linke Werkzeugleiste)
- Einstellungen-Dialog: Auto-Größe berücksichtigt jetzt auch die
  benötigte Breite der Tab-Leiste selbst
- Garn-Vorrat-Button in die Werkzeugleiste geholt (vorher nur im
  Bearbeiten-Menü versteckt)
- Layer-Panel-Buttons, Custom-Tooltip statt QToolTip, Modus-Switch
  deutlicher sichtbar

### Behoben

- Settings-Dialog Theme-Bug, PDF/HTML-Export i18n-Lücke
- Doppelte Tastenkürzel (Garn-Vorrat vs. Muster-Import, Farbe ersetzen
  vs. hervorheben)
- ARCHITECTURE.md: Mixin-Zahl korrigiert (sechs -> acht)

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
