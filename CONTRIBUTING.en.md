# Contributing to PySticky

*[Deutsch](CONTRIBUTING.md) | English*

Great that you want to contribute! PySticky is a PySide6/Qt application for
designing cross-stitch patterns. Contributions of all kinds are welcome — bug
fixes, features, translations, documentation.

## Setting up the development environment

```bash
git clone https://github.com/HasoSchno70/Pysticky.git
cd Pysticky

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -e ".[dev]"   # PySticky + pytest, pytest-qt, ruff
python run.py             # Start the app
```

## Before every pull request

Please make sure these three things are green:

```bash
py -m pytest tests/ -x        # all tests pass
py -m ruff check src/ tests/  # no lint errors
py -m ruff format src/ tests/ # consistent formatting
```

Optional but recommended: enable pre-commit hooks, then lint and formatting
run automatically on every commit:

```bash
pip install pre-commit
pre-commit install
```

## Code Style & Conventions

- **Formatting/Lint:** `ruff` (rules `E,F,W,I,N`, `line-length=100`).
  Deliberate exceptions are listed in `[tool.ruff.lint.per-file-ignores]` in
  `pyproject.toml`.
- **Language:** The source language is German. UI strings are wrapped in
  `t("...")` (see `core/i18n.py`); English translations are added in
  `resources/i18n/en.json`. Careful: don't create a local variable named `t`
  when `t` is imported (name collision).
- **Architecture:** Please read [ARCHITECTURE.en.md](ARCHITECTURE.en.md)
  beforehand — it explains the layers (core/io/ui/plugins), the mixin
  pattern, and the theme system. Domain logic belongs in `core/` (without a
  Qt dependency, so it stays testable).
- **New features** should be backed by tests in `tests/` wherever possible.

## Pull Request Workflow

1. Fork the repo and create a branch (`git checkout -b my-feature`).
2. Commit with a meaningful message.
3. Tests + lint + format green (see above).
4. Open a pull request and briefly describe what and why.

## Bugs & Ideas

Open an [issue](https://github.com/HasoSchno70/Pysticky/issues) with steps to
reproduce (for bugs) or a brief description of the suggestion (for ideas).
Screenshots help.

Thanks for contributing! 🧵
