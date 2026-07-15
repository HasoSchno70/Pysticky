# Mitmachen bei PySticky

*Deutsch | [English](CONTRIBUTING.en.md)*

Schön, dass du beitragen möchtest! PySticky ist ein PySide6/Qt-Programm zum
Entwerfen von Kreuzstichmustern. Beiträge aller Art sind willkommen — Bugfixes,
Features, Übersetzungen, Doku.

## Entwicklungsumgebung einrichten

```bash
git clone https://github.com/HasoSchno70/Pysticky.git
cd Pysticky

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -e ".[dev]"   # PySticky + pytest, pytest-qt, ruff
python run.py             # App starten
```

## Vor jedem Pull Request

Bitte stelle sicher, dass diese drei Dinge grün sind:

```bash
py -m pytest tests/ -x        # alle Tests bestehen
py -m ruff check src/ tests/  # keine Lint-Fehler
py -m ruff format src/ tests/ # einheitliche Formatierung
```

Optional, aber empfohlen: Pre-commit-Hooks aktivieren, dann laufen Lint und
Format automatisch bei jedem Commit:

```bash
pip install pre-commit
pre-commit install
```

## Codestil & Konventionen

- **Formatierung/Lint:** `ruff` (Regeln `E,F,W,I,N`, `line-length=100`).
  Bewusste Ausnahmen stehen in `[tool.ruff.lint.per-file-ignores]` in
  `pyproject.toml`.
- **Sprache:** Quellsprache ist Deutsch. UI-Strings in `t("...")` wickeln
  (siehe `core/i18n.py`); englische Übersetzungen in
  `resources/i18n/en.json` ergänzen. Achtung: keine lokale Variable `t`
  anlegen, wenn `t` importiert ist (Namenskollision).
- **Architektur:** Bitte vorher [ARCHITECTURE.md](ARCHITECTURE.md) lesen —
  erklärt die Schichten (core/io/ui/plugins), das Mixin-Muster und das
  Theme-System. Domänenlogik gehört nach `core/` (ohne Qt-Abhängigkeit, damit
  testbar).
- **Neue Features** möglichst mit Tests in `tests/` absichern.

## Pull-Request-Ablauf

1. Forke das Repo und erstelle einen Branch (`git checkout -b mein-feature`).
2. Commit mit aussagekräftiger Nachricht.
3. Tests + Lint + Format grün (siehe oben).
4. Pull Request öffnen und kurz beschreiben, was und warum.

## Bugs & Ideen

Eröffne ein [Issue](https://github.com/HasoSchno70/Pysticky/issues) mit
Schritten zum Reproduzieren (bei Bugs) bzw. einer kurzen Beschreibung des
Vorschlags. Screenshots helfen.

Danke fürs Mitmachen! 🧵
