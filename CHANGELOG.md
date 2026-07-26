# Changelog

*Deutsch | [English](CHANGELOG.en.md)*

Alle nennenswerten Änderungen an PySticky werden hier dokumentiert.

Format angelehnt an [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
Versionierung an [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

## [1.1.0] — 2026-07-26

Ergebnis einer mehrtägigen, systematischen Clean-Code-Audit-Serie (über 80
Runden) über die gesamte Codebasis — Modul für Modul auf Datenverlust-Risiken,
Absturz-Kandidaten und stillschweigend falsches Verhalten geprüft. Kein
einzelnes Highlight, sondern viele kleine bis mittlere Korrekturen, die in
Summe Undo, Rückstiche, Diamond-Painting-Modus und den Im-/Export deutlich
robuster machen.

### Geändert

- Farbe ersetzen: neuer Vorschlags-Dialog zeigt die ähnlichsten Farben der
  Palette als Kacheln (mit Verwendungszahl) und bietet eine automatische
  Reduzierung selten verwendeter Farben ("Konfetti") auf die jeweils
  ähnlichste häufige Farbe
- Zoom per Mausrad ankert jetzt auf der Cursor-Position statt auf der
  Canvas-Mitte
- Tweed-Blend-Farben werden in Garnverbrauch-Tab, Einkaufsliste und
  CSV-Export jetzt korrekt auf ihre echten Garn-Komponenten aufgelöst statt
  als ein Posten gezählt
- CSV-Exporte (Garnliste, Statistik) schreiben jetzt ein UTF-8-BOM, damit
  Excel Umlaute korrekt anzeigt

### Behoben

**Speichern, Undo & Autosave**

- Speichern eines Musters mit nicht-serialisierbarem Zustand konnte die App
  abstürzen lassen statt einen Fehlerdialog zu zeigen; Autosave- und
  Snapshot-Fehler werden jetzt geloggt statt lautlos verschluckt
- "Ebene leeren" umging komplett das Undo-System; mehrere Werkzeuge
  (Auswahl-Verschieben, Farbverlauf, Select/Lasso) verloren den Stichtyp bei
  Undo/Verschieben/Drehen/Spiegeln/Einfügen
- Wechsel zwischen Kreuzstich- und Diamond-Painting-Modus leerte den
  Undo-Verlauf nicht, was zu inkonsistenten Wiederherstellungen führen
  konnte; Plugin-Undo (`LayerSnapshotCommand`) merkte sich nur den
  Layer-Index statt einer echten Objektreferenz und konnte abstürzen, wenn
  ein Plugin die Mustergröße änderte
- Autosave-Kollision: mehrere gleichzeitig laufende Instanzen mit nie
  gespeichertem Muster überschrieben sich gegenseitig über denselben
  Temp-Pfad; vier weitere Autosave-/Snapshot-Recovery-Bugs behoben; eine
  beschädigte Autosave-Datei ließ die App beim Start abstürzen statt eine
  Fehlermeldung zu zeigen; die Datei-Autosave-Recovery war zeitweise
  komplett wirkungslos
- Massen-Operationen (Farbe ersetzen, Füllen, Spiegeln) auf großen Mustern
  konnten die Oberfläche minutenlang einfrieren, weil Panel-Updates pro
  Stich statt einmal pro Vorgang ausgelöst wurden

**Ebenen-Sperre**

- Mehrere Werkzeuge (Radierer, Zeichenwerkzeuge, Auswahl-Verschieben)
  respektierten die Ebenen-Sperre nicht konsequent und erzeugten teils
  wirkungslose Undo-Einträge; das Fortschritts-Werkzeug (Stiche als erledigt
  markieren) wurde umgekehrt fälschlich durch die Sperre blockiert, obwohl
  das Markieren auf gesperrten Ebenen weiter möglich sein soll

**Rückstiche**

- Rückstiche gingen beim Drehen, Spiegeln, Zuschneiden oder Ändern der
  Mustergröße verloren; verschwanden exakt am Musterrand aus dem
  HTML-Export; wurden von Pattern-Diff und der Vorschau-Linienstil-Anzeige
  ignoriert; erschienen im Diamond-Painting-Modus fälschlich trotzdem
- "Farbe ersetzen"/"Farbe tauschen" ließ den geerbten Halbstich-/
  Bead-Stichtyp an der falschen Farbe hängen; "Farbe entfernen" ließ
  Rückstiche verwaisen; Löschen traf bei mehreren nahen Linien immer die
  älteste statt die tatsächlich angeklickte
- XSD-, OXS- und PAT-Import ließen Rückstich-Koordinaten sowie
  abgeschnittene oder unvollständige Grid-Daten ungeprüft durch; OXS-Import
  verschluckte kaputte Referenzen und Float-Koordinaten stumm

**Diamond-Painting-Modus**

- Mehrere Stellen zeigten weiterhin Kreuzstich-Vokabular statt
  Diamond-Painting-Begriffen (Zeitschätzung-Tab, Einkaufsliste,
  Rahmenaufteilung-Dialog, Info-Panel-Tooltip); die Diamond-Farbliste zeigte
  Garn-Meter statt Drill-Anzahl
- Diamond-Drills fehlten im Chunk-Cache-Renderpfad und im Bild-Export
  (wurden dort als flaches Quadrat statt als Drill gerendert); die
  Drill-Rendering-Logik war an drei Stellen dupliziert und ist jetzt
  konsolidiert

**Theme-Wechsel**

- Mehrere UI-Elemente behielten nach einem Live-Theme-Wechsel ihr altes
  Aussehen: die Symbolleiste, StatCard-Icons, die Sticken-Modus-Anzeige, der
  Diamond-Painting-Tooltip sowie Zeilen im Ebenen-Panel; die Statistik-
  Tabellen zeigten Farb-Swatches in jeder zweiten Zeile gar nicht an

**Import & Export**

- Mystery-Modus verriet die Rückstich-Kontur weiterhin im HTML-Export und
  wurde vom Bundle-Export komplett ignoriert
- PDF-Export konnte durch bestimmten Nutzertext zum Absturz gebracht werden;
  die Farb-Legende verlor bei vielen Farben die Spaltenkopfzeile auf
  Folgeseiten; PDF-Schutz-Checkboxen ohne gesetztes Passwort waren
  wirkungslos, das Passwort wurde nicht getrimmt; das Deckblatt zeigte kein
  Stickdatum
- Bild-Export ließ Rückstich-Konturlinien komplett weg
- Drag & Drop lehnte die Bildformate WebP, TIFF und AVIF am Fenster ab
- Muster-Bibliothek ließ veraltete Thumbnails und doppelte Pfade durch

**Farbverwaltung**

- Zusammenführen ähnlicher Farben verlor die Halb-/Viertelstich- sowie die
  Bead-/Diamond-Stempelung der betroffenen Stiche
- Bei mehr als 86 Farben vergab der Bildimport das Ersatzsymbol "?"
  mehrfach statt eindeutig zu bleiben; der Import einer eigenen Palette
  ließ Farben ohne Katalognummer auf einen einzigen Eintrag kollabieren;
  der Tweed-Blend-Dialog erzeugte bei wiederholtem Mischen
  Palette-Duplikate
- Die Einkaufsliste rechnete den Vorrat bei doppelt vorhandenem Garn
  mehrfach gegen

**Werkzeuge & Canvas**

- Das Farbverlauf-Werkzeug hatte eine wirkungslose Live-Vorschau, verwarf
  die Panel-Startfarbe und blockierte komplett bei einer Ein-Farben-Palette
- Die Pipette nahm bei mehreren Ebenen gelegentlich die falsche Farbe auf;
  die Spiegel-Cursor-Vorschau konnte eine gespiegelte Zelle je nach
  Reihenfolge überspringen; das Polygon-Füllwerkzeug lief bei Klicks
  außerhalb des Musters unbegrenzt weiter
- Zeichenwerkzeuge: die Ellipse kollabierte bei sehr kleinen Zügen, die
  Linie war richtungsabhängig, das Rechteck erzeugte doppelte Randpunkte
- Der Zoom-Regler hing bei individuell eingestellten Zellgrößen fest
- Farb-Ersatz per Drag & Drop auf die Farbleiste war praktisch nie
  auslösbar, weil das Farbfeld keine Drag-Bewegung akzeptierte

**Dialoge & Oberfläche**

- Das Raster-Optionen-Dialogfeld wirkte nur auf die laufende Sitzung, nie
  auf die gespeicherten Einstellungen; die Dock-Layout-Persistenz war
  komplett wirkungslos; gespeicherte Tastenkürzel-Overrides wurden ohne
  Kollisionsprüfung angewendet
- Der Neues-Projekt-Dialog ließ Diamond-Painting-Preset- und
  Eigene-Vorlage-Zustand zwischen Aufrufen hängen; ein Abbruch zeigte
  keinen Willkommensbildschirm mehr an
- Der Bildimport-"Wizard Recall" (Import erneut mit anderen Einstellungen
  öffnen) verlor dabei Muster-Eigenschaften
- Der Symbol-Editor ignorierte den konfigurierten Symbol-Font
- Vorlagen ließen sich beim Speichern/Umbenennen unter Duplikat-Namen
  ablegen
- Ein sehr breiter Custom-Tooltip-Text konnte komplett aus dem Bildschirm
  rutschen
- "Zuletzt geöffnet" stürzte bei einem inzwischen gelöschten Eintrag ab
- Der Heatmap-Dialog ignorierte Größenänderungen, normalisierte
  Randblöcke falsch und zählte übersprungene (skip_stitching) Farben in
  die Auswertung mit ein; ein Rahmenaufteilung-Dialog mit winzigem Rahmen
  und hoher Überlappung fror komplett ein
- Die Farbliste im Info-Panel schnitt mehrzeichige Ersatzsymbole am
  Zellrand ab und folgte nach Löschen/Umsortieren nicht mehr der
  richtigen Farbe
- Die Statistik-"Abdeckung"-Karte zeigte bei mehreren gefüllten Ebenen
  über 100 % an
- Das zuvor tote Rückstich-Optionen-Panel ist jetzt verdrahtet und
  unterstützt auch den Spiegel-Modus

**Internationalisierung, Bedienbarkeit & Plattform**

- 52 fehlende Übersetzungen ergänzt, dazu mehrere einzelne Nachträge
- Drei echte Bedienbarkeits-Bugs für Tastatur-/Screenreader-Nutzung
  behoben
- Zahlen-Eingabefelder zeigten ohne explizite Locale ein Komma statt
  eines Punkts an; ein Tooltip in der Versionshistorie zeigte hartcodiert
  englische Wochentagsnamen
- Auf macOS schlug das Öffnen von Export-Ordnern lautlos fehl, weil
  `xdg-open` dort nicht existiert
- Ein von Hand editrierter Registrierungswert ohne korrekten Typ ließ die
  Einstellungs-Tabs abstürzen

**Robustheit gegen beschädigte Dateien**

- Beschädigte JSON-/Metadaten-Werte konnten die Übersetzungs-Verwaltung,
  den Garn-Vorrat und den Sitzungs-Timer zum Absturz bringen; ein
  fehlerhaftes Plugin-Manifest mit falscher Zeichenkodierung ebenso
- Nicht-Objekt-Einträge in Farben-, Ebenen- und Rückstich-Listen einer
  Datei werden jetzt abgefangen statt die App abstürzen zu lassen
- Zwei bislang lautlos verschluckte Speicherfehler sind jetzt sichtbar

## [1.0.1] — 2026-07-19

### Hinzugefügt

- Windows-Installer (`PySticky-Setup.exe`) als zusätzliche Download-Option
  neben der portablen `.exe` — mit Start-Menü-Eintrag, optionalem
  Desktop-Icon und Deinstaller

### Behoben

- Diamond-Painting-Modus: Info-Panel-Tooltip fiel nach dem ersten
  Stich-Update auf Kreuzstich-Wortlaut zurück statt im Diamond-Modus zu
  bleiben
- Statistik-Dialog blendet Garnverbrauch-/Einkaufsliste-Tabs jetzt im
  Diamond-Painting-Modus aus (Strang-Berechnung ergibt für Diamanten
  keinen Sinn); Fortschritt-Tab sagt "Diamanten gesetzt" statt "Stiche
  gestickt"
- "Sticken-Modus" (Ctrl+M) und "Tweed-Blend erzeugen" sind im
  Diamond-Painting-Modus jetzt deaktiviert statt wirkungslos anklickbar
  zu bleiben
- CI-Workflow: `GITHUB_TOKEN` des Test-Jobs hatte keine eingeschränkten
  Rechte (CodeQL-Fund, CWE-275) — jetzt explizit auf Lesezugriff begrenzt

## [1.0.0] — 2026-07-18

### Behoben

- **Kritisch:** auf großen Mustern (> 200×200 Zellen, z.B. Wandbilder)
  blieben neu gezeichnete Stiche auf dem Canvas unsichtbar — der
  Chunk-Pixmap-Cache wusste nie, dass sich eine Zelle geändert hatte, und
  zeigte weiterhin den alten (meist leeren) gerenderten Chunk
- Zoomen auf einem großen Muster zeigte danach falsch skalierte,
  verschobene Blöcke — derselbe Chunk-Cache invalidierte sich auch beim
  Zoomen nie; behoben durch echte Kontrolle der Render-Parameter statt nur
  der Zellkoordinaten
- Aida-Stoff-Textur fehlte komplett auf großen Mustern (Chunk-Cache-Pfad
  zeichnete leere Zellen nur einfarbig statt mit der Stoff-Optik)
- Gitterlinien waren gegen die Hintergrundfarbe leerer Zellen praktisch
  unsichtbar (WCAG-Kontrast ~1,0–1,4:1) — jetzt automatisch kontrastsicher
  für jede gewählte Farbkombination
- Standardfarbe für leere Zellen war versehentlich dunkelblau statt der
  vorgesehenen Stoff-Cremefarbe
- Zeichnen auf einem Muster ohne hinzugefügte Farbe erzeugte unsichtbare,
  aber mitgezählte Stiche (Stich-Zähler stieg, Canvas blieb leer) — wird
  jetzt abgelehnt statt lautlos falsche Daten zu erzeugen
- "Neu" legte ein Muster ganz ohne Farbe an, sodass sofortiges Zeichnen
  nichts bewirkte — ein neues Muster startet jetzt automatisch mit der
  ersten Farbe der konfigurierten Standardpalette
- Statusleisten-Kontrast: Text nutzte auf mehreren Pills dieselbe
  Akzentfarbe wie der Hintergrund-Tint und war kaum lesbar
- Farben-, Allgemein-, Dateien-, Werkzeuge- und Canvas-Settings-Tab: 39
  Einstellungen waren totes UI (schrieben nur in QSettings, wurden nie
  gelesen) — jetzt vollständig verdrahtet. Nicht sinnvoll umsetzbare
  Optionen (PDF-Qualität, HTML-Inline-CSS, Auswahl-Hinzufügen/Subtrahieren)
  wurden stattdessen aus der Oberfläche entfernt statt vorgetäuscht

## [0.9.0] — 2026-07-17

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
