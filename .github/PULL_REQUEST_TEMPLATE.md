## Was & Warum / What & Why

Kurze Beschreibung der Änderung und der Motivation dahinter.
*Brief description of the change and the motivation behind it.*

Schließt # (falls zutreffend) / Closes # (if applicable)

## Art der Änderung / Type of Change

- [ ] Bugfix
- [ ] Neues Feature / New feature
- [ ] Breaking Change
- [ ] Doku / Docs
- [ ] Sonstiges (Refactoring, Tests, ...) / Other (refactoring, tests, ...)

## Checkliste / Checklist

- [ ] `py -m pytest tests/ -x` läuft grün / passes
- [ ] `py -m ruff check src/ tests/` ohne Fehler / no errors
- [ ] `py -m ruff format src/ tests/` angewendet / applied
- [ ] Neue/geänderte UI-Strings sind mit `t("...")` gewickelt und in
      `resources/i18n/en.json` ergänzt (falls zutreffend) /
      New/changed UI strings are wrapped in `t("...")` and added to
      `resources/i18n/en.json` (if applicable)
- [ ] Neue Logik hat Tests in `tests/` (falls sinnvoll möglich) /
      New logic has tests in `tests/` (where reasonably possible)
- [ ] [ARCHITECTURE.md](../ARCHITECTURE.md) / [ARCHITECTURE.en.md](../ARCHITECTURE.en.md)
      berücksichtigt (Domänenlogik in `core/`, kein Qt dort) /
      considered (domain logic in `core/`, no Qt there)

## Screenshots (falls UI-Änderung / if UI change)
