## Was & Warum

Kurze Beschreibung der Änderung und der Motivation dahinter.

Schließt # (falls zutreffend)

## Art der Änderung

- [ ] Bugfix
- [ ] Neues Feature
- [ ] Breaking Change
- [ ] Doku
- [ ] Sonstiges (Refactoring, Tests, ...)

## Checkliste

- [ ] `py -m pytest tests/ -x` läuft grün
- [ ] `py -m ruff check src/ tests/` ohne Fehler
- [ ] `py -m ruff format src/ tests/` angewendet
- [ ] Neue/geänderte UI-Strings sind mit `t("...")` gewickelt und in
      `resources/i18n/en.json` ergänzt (falls zutreffend)
- [ ] Neue Logik hat Tests in `tests/` (falls sinnvoll möglich)
- [ ] [ARCHITECTURE.md](../ARCHITECTURE.md) berücksichtigt (Domänenlogik in `core/`, kein Qt dort)

## Screenshots (falls UI-Änderung)
