# Changelog

*Deutsch | [English](CHANGELOG.en.md)*

Alle nennenswerten Änderungen an PySticky werden hier dokumentiert.

Format angelehnt an [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
Versionierung an [Semantic Versioning](https://semver.org/lang/de/) (solange
vor 1.0: `0.MINOR.PATCH`, Breaking Changes möglich innerhalb 0.x).

## [Unreleased]

## [0.9.0] — 2026-07-17

### Hinzugefügt

- Farb-Toleranz (ΔE) beim Füllen und bei "Farbe ersetzen" — ersetzt/füllt
  jetzt auch ähnliche statt nur exakt gleiche Farben
- "Mystery-Modus" (Einstellungen → Dateien → Export): druckt Musterseiten
  ohne Farben (nur Symbol + Gitter) für Überraschungs-Kits
- "Bildimport wiederholen…" (Datei-Menü): öffnet den Import-Dialog
  vorbefüllt mit Quellbild, Ausschnitt und Einstellungen des aktuellen
  Musters, um den Import mit angepassten Werten zu wiederholen
- Farbe-ersetzen-Dialog komplett überarbeitet: Vorschlags-Kacheln mit den
  ähnlichsten Farben, große Original-➜-Neu-Vorschau, Auto-Reduzieren
  seltener Farben in einem Schritt
- Datei-Logging (Einstellungen → Diagnose) — schreibt bei Bedarf alle
  Fehler nach `~/.pysticky/logs`
- "Tastenkürzel"-Settings-Tab ist jetzt echt verdrahtet (vorher wirkungslos)
- Anchor-Palette um 76 zuvor fehlende Farben ergänzt, danach komplett auf
  eine verifizierte Quelle (stitchmate.app) umgestellt; DMC und Cosmo
  ebenso (Cosmo 91 → 542 Farben)

### Geändert

- Farbabstand-Metrik überall von CIE76 auf CIEDE2000 upgegradet
  (genauere Farbtoleranz/Ähnlichkeits-Berechnung)
- Diamond Painting zeigt jetzt überall Farb-Symbole statt DMC-Nummern
  (Canvas, HTML-/PDF-Export)
- Madeira-Paletten konsolidiert: unklare, herkunftsungeklärte 269-Farben-
  Datei entfernt, verifizierte Mouliné-Palette (381 Farben) ist jetzt die
  alleinige "Madeira"-Palette
- Dialog-Feinschliff: doppelte Titel-Zeilen in 6 Dialogen entfernt (Titel
  steht schon in der Fensterleiste), Innenabstände über ~23 Dialoge
  vereinheitlicht
- Statistik-Dialog (1078 → 297 Zeilen) und Bildimport-Dialog
  (1110 Zeilen → 6 Module) intern aufgeteilt — keine sichtbare Änderung,
  nur wartbarer

### Behoben

- **Kritisch:** 10 Garnpaletten (u.a. Cosmo, Finca, Olympus, Valdani,
  Weeks Dye Works) hatten nie eine erkennbare Katalognummer — ein
  Bildimport in eine dieser Paletten ließ das gesamte Muster auf eine
  einzige Farbe kollabieren
- Gitterlinien waren gegen gedeckte/graue Garnfarben (z.B. Wasser/Himmel
  bei Foto-Importen) kaum sichtbar — Kontrast deutlich erhöht
- Speichern-Absturz bei nicht-serialisierbarem Zustand
- "Farbe ersetzen" bei großen Mustern: minutenlanger UI-Freeze durch
  Massen-Operationen behoben (jetzt ~0,25s statt Minuten)
- Lineal und Start-Bildschirm aktualisierten sich nicht live bei
  Theme-Wechsel
- Absturz beim Farbe-Löschen und Spiegeln (nicht existierendes
  `clear_stitch`)
- Zwei echte Tastenkürzel-Kollisionen gefunden und behoben
  (`action_save_as`/`action_statistics`, u.a.)
- Statistik-Tabellen: Farb-Swatches in geraden Zeilen waren unsichtbar

## [0.8.2] — 2026-07-15

### Behoben

- Heatmap-Dialog öffnete sich gar nicht (Schleifenvariable `t` überschrieb
  die Übersetzungsfunktion `t()`, stiller Absturz beim Aufbau)
- Bild-Import-Dialog: linke Einstellungs-Spalte (v.a. "Farben"-Sektion)
  wirkte gestaucht/schwer lesbar bei fixer Default-Größe
- Windows-Autoscroll-Toast ("Scrollen deaktiviert") beim Ziehen im
  Bild-Import-Zuschnitt (fehlendes `event.accept()` bei Mittelklick)
- Custom-Tooltip konnte bei kleinen Widgets (z.B. Spinbox) die eigene
  Zahl verdecken statt darunter zu erscheinen
- Statistik-Dialog: Tab-Leiste (6 Tabs inkl. "Einkaufsliste") wurde bei
  schmalen Bildschirmen abgeschnitten; Mindestbreite jetzt fest auf
  1200px, dazu ein Bug in der Auto-Größen-Berechnung behoben, der die
  Mindestbreite für die Tab-Leiste wieder unterschreiten konnte
- Screen-Eyedropper matchte gepickte Farben gegen alle geladenen
  Garnpaletten statt nur die aktuell gewählte — konnte Farben eines
  fremden Herstellers ins Muster bringen

### Geändert

- "Multi-Hoop-Planer" umbenannt zu "Rahmenaufteilung" ("Multi-Hoop" ist
  ein Maschinenstickerei-Fachbegriff, im Handkreuzstich nicht gebräuchlich)

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
