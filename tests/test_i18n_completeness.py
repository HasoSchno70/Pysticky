# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 18): systematischer Abgleich aller t("...")-Aufrufe
mit direkten String-Literalen gegen resources/i18n/en.json. Vorher gab es
KEINEN Test, der pruefte, ob jede t()-Quellstring tatsaechlich eine
Uebersetzung hat -- nur ob t() selbst nicht abstuerzt
(test_i18n_en_smoke.py). Ein Audit deckte 52 fehlende Uebersetzungen auf,
u.a. fast die komplette Hilfetexte von inventory_dialog.py (13 von 36
Strings, 64% Abdeckung). Dieser Test verhindert, dass zukuenftige neue
t()-Aufrufe wieder unbemerkt ohne Uebersetzung bleiben.

Erfasst nur DIREKTE String-Literal-Argumente von t(...) per AST (keine
dynamischen/indirekten Quellen wie t(variable) -- die muessten separat
gegen ihre jeweilige Datenquelle geprueft werden, siehe Round-18-Notiz in
memory fuer die bereits gefixten Faelle: tool_enum.py, time_tab.py,
new_project_dialog.py).
"""

import ast
import json
from pathlib import Path

SRC_ROOT = Path(__file__).parent.parent / "src" / "pysticky"
EN_JSON_PATH = SRC_ROOT / "resources" / "i18n" / "en.json"


def _extract_t_call_literals() -> dict[str, list[str]]:
    """Sammelt alle direkten String-Literal-Argumente von t(...)-Aufrufen,
    gruppiert nach relativem Dateipfad."""
    by_file: dict[str, list[str]] = {}
    for pyfile in SRC_ROOT.rglob("*.py"):
        try:
            src = pyfile.read_text(encoding="utf-8")
            tree = ast.parse(src, filename=str(pyfile))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "t"
                and len(node.args) == 1
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                rel = str(pyfile.relative_to(SRC_ROOT))
                by_file.setdefault(rel, []).append(node.args[0].value)
    return by_file


def test_every_direct_t_call_literal_has_an_english_translation():
    en = json.loads(EN_JSON_PATH.read_text(encoding="utf-8"))
    by_file = _extract_t_call_literals()

    missing: list[str] = []
    for rel_file, strings in sorted(by_file.items()):
        for s in strings:
            if s not in en:
                missing.append(f"{rel_file}: {s!r}")

    assert not missing, (
        f"{len(missing)} t()-Aufruf(e) ohne en.json-Uebersetzung "
        f"(zeigen im Englisch-Modus deutschen Text):\n" + "\n".join(missing)
    )
