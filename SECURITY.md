# Sicherheitsrichtlinie

## Unterstützte Versionen

PySticky ist derzeit vor der 1.0-Veröffentlichung. Unterstützt wird immer nur
der aktuelle Stand auf `main`:

| Version | Unterstützt |
| ------- | ----------- |
| main    | ✅          |
| ältere Tags/Releases | ❌ |

## Eine Sicherheitslücke melden

Bitte melde Sicherheitslücken **nicht** über ein öffentliches Issue.

Nutze stattdessen GitHub's private Sicherheitsmeldung:
[Security → Report a vulnerability](https://github.com/HasoSchno70/Pysticky/security/advisories/new)
(Tab „Security“ im Repository, falls der Link nicht direkt funktioniert).

Bitte gib nach Möglichkeit an:
- Betroffene Version/Commit
- Schritte zum Reproduzieren
- Mögliche Auswirkung (z.B. Codeausführung, Datenverlust, Denial of Service)

## Was du erwarten kannst

- Eine Rückmeldung, sobald die Meldung gesichtet wurde
- Eine Einschätzung, ob und wie das Problem behoben wird
- Nennung als Melder:in im Fix (Commit/Release-Notes), falls gewünscht

PySticky ist eine lokale Desktop-Anwendung ohne Server-Backend und ohne
Netzwerk-Kommunikation mit Nutzerdaten. Relevante Angriffsflächen sind vor
allem das Einlesen von Datei-Formaten (`.pxs`, OXS/XSD/PAT, Bild-Import) —
Meldungen zu Abstürzen oder unerwartetem Verhalten beim Öffnen präparierter
Dateien sind besonders willkommen.
