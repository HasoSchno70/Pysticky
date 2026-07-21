# -*- coding: utf-8 -*-
"""Tests fuer das Plugin-System."""

import json
from typing import Optional

import pytest

# ---------- Mock-Context fuer headless Tests ----------


class MockContext:
    """Headless-Implementation des PluginContext-Protocols."""

    def __init__(
        self,
        int_answers: Optional[list[int]] = None,
        str_answers: Optional[list[str]] = None,
    ) -> None:
        self.int_answers = int_answers or []
        self.str_answers = str_answers or []
        self.messages: list[str] = []
        self.errors: list[str] = []
        self.progress_calls: list[tuple[float, str]] = []

    def show_message(self, text: str) -> None:
        self.messages.append(text)

    def show_error(self, text: str) -> None:
        self.errors.append(text)

    def prompt_int(
        self,
        question: str,
        default: int = 0,
        minimum: int = 0,
        maximum: int = 1_000_000,
    ) -> Optional[int]:
        if self.int_answers:
            return self.int_answers.pop(0)
        return default

    def prompt_str(self, question: str, default: str = "") -> Optional[str]:
        if self.str_answers:
            return self.str_answers.pop(0)
        return default

    def progress(self, value: float, text: str = "") -> None:
        self.progress_calls.append((value, text))


# ---------- API-Tests ----------


def test_manifest_from_dict_requires_id_name_version():
    """Manifest braucht die drei Pflichtfelder."""
    from pysticky.plugins import PluginError, PluginManifest

    with pytest.raises(PluginError):
        PluginManifest.from_dict({"name": "x", "version": "1"})


def test_manifest_from_dict_defaults():
    """Optionale Felder kriegen sinnvolle Defaults."""
    from pysticky.plugins import PluginManifest

    m = PluginManifest.from_dict({"id": "x", "name": "X", "version": "1.0"})
    assert m.entry_module == "plugin"
    assert m.entry_function == "run"
    assert m.description == ""


def test_discover_finds_builtin_plugins():
    """Built-in-Plugins werden gefunden (Border, Schachbrett, Symmetrie)."""
    from pysticky.plugins import discover_plugins

    plugins = discover_plugins()
    ids = {p.id for p in plugins}
    assert "pysticky.border" in ids
    assert "pysticky.checkerboard" in ids
    assert "pysticky.mirror_horizontal" in ids


def test_discover_skips_invalid_manifest(tmp_path):
    """Ein Verzeichnis mit kaputtem manifest.json wird uebersprungen, nicht crashed."""
    from pysticky.plugins import discover_plugins

    bad_dir = tmp_path / "bad_plugin"
    bad_dir.mkdir()
    (bad_dir / "manifest.json").write_text("not json", encoding="utf-8")

    plugins = discover_plugins(extra_dirs=[tmp_path])
    # Built-ins werden gefunden, bad_plugin wird uebersprungen
    bad_ids = {p.id for p in plugins if "bad" in p.id.lower()}
    assert not bad_ids


def test_discover_deduplicates_by_id(tmp_path):
    """Doppelte Plugin-IDs werden nur einmal geliefert."""
    from pysticky.plugins import discover_plugins

    # Duplizieren eine der Built-in-Plugin-IDs
    dup_dir = tmp_path / "dup_border"
    dup_dir.mkdir()
    (dup_dir / "manifest.json").write_text(
        json.dumps({"id": "pysticky.border", "name": "Border 2", "version": "1.0"}),
        encoding="utf-8",
    )
    (dup_dir / "plugin.py").write_text("def run(p, c): pass\n", encoding="utf-8")

    plugins = discover_plugins(extra_dirs=[tmp_path])
    border_plugins = [p for p in plugins if p.id == "pysticky.border"]
    assert len(border_plugins) == 1


def test_run_plugin_calls_function(tmp_path, empty_pattern):
    """Ein einfaches Plugin wird ausgefuehrt und die Run-Funktion aufgerufen."""
    from pysticky.plugins import Plugin, PluginManifest, run_plugin

    plugin_dir = tmp_path / "test_plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.py").write_text(
        "called = False\ndef run(pattern, ctx):\n    ctx.show_message('hello from plugin')\n",
        encoding="utf-8",
    )

    plugin = Plugin(
        manifest=PluginManifest(
            id="test.simple",
            name="Test",
            version="1.0",
            description="",
        ),
        directory=plugin_dir,
    )
    ctx = MockContext()
    run_plugin(plugin, empty_pattern, ctx)
    assert "hello from plugin" in ctx.messages


def test_run_plugin_raises_on_missing_module(tmp_path, empty_pattern):
    """Fehlendes plugin.py liefert PluginError."""
    from pysticky.plugins import Plugin, PluginError, PluginManifest, run_plugin

    plugin_dir = tmp_path / "no_module"
    plugin_dir.mkdir()
    # KEIN plugin.py erstellt

    plugin = Plugin(
        manifest=PluginManifest(id="test.missing", name="Missing", version="1.0", description=""),
        directory=plugin_dir,
    )
    with pytest.raises(PluginError):
        run_plugin(plugin, empty_pattern, MockContext())


def test_run_plugin_raises_on_missing_function(tmp_path, empty_pattern):
    """plugin.py ohne run-Funktion liefert PluginError."""
    from pysticky.plugins import Plugin, PluginError, PluginManifest, run_plugin

    plugin_dir = tmp_path / "no_run"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.py").write_text("# kein run hier\n", encoding="utf-8")

    plugin = Plugin(
        manifest=PluginManifest(id="test.norun", name="NoRun", version="1.0", description=""),
        directory=plugin_dir,
    )
    with pytest.raises(PluginError):
        run_plugin(plugin, empty_pattern, MockContext())


def test_run_plugin_wraps_plugin_errors(tmp_path, empty_pattern):
    """Wenn ein Plugin selber crashed, wird das in PluginError gewrappt."""
    from pysticky.plugins import Plugin, PluginError, PluginManifest, run_plugin

    plugin_dir = tmp_path / "crashy"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.py").write_text(
        "def run(pattern, ctx):\n    raise RuntimeError('oops')\n",
        encoding="utf-8",
    )

    plugin = Plugin(
        manifest=PluginManifest(id="test.crashy", name="Crashy", version="1.0", description=""),
        directory=plugin_dir,
    )
    with pytest.raises(PluginError, match="oops"):
        run_plugin(plugin, empty_pattern, MockContext())


# ---------- Built-in Plugin-Funktions-Tests ----------


def test_border_plugin_draws_rectangle(empty_pattern):
    """Border-Plugin zeichnet einen Rahmen am Rand."""
    from pysticky.core import Thread
    from pysticky.plugins import discover_plugins, run_plugin

    pattern = empty_pattern  # 10x10
    pattern.add_color(Thread.from_hex("Red", "#FF0000"))

    plugins = {p.id: p for p in discover_plugins()}
    border = plugins["pysticky.border"]

    ctx = MockContext(int_answers=[1, 1])  # margin=1, thickness=1
    run_plugin(border, pattern, ctx)

    # Stiche an den vier Eckpunkten margin=1
    layer = pattern.layer_stack.active_layer
    # (1, 1), (8, 1), (1, 8), (8, 8) sollten gesetzt sein
    assert layer.get_stitch(1, 1) is not None
    assert layer.get_stitch(8, 1) is not None
    assert layer.get_stitch(1, 8) is not None
    assert layer.get_stitch(8, 8) is not None
    # Mitte sollte LEER sein
    assert layer.get_stitch(5, 5) is None


def test_border_plugin_does_not_double_count_middle_row(empty_pattern):
    """Regression: bei ungerader Breite/Höhe kann die Mitte gleichzeitig
    oberer UND unterer (bzw. linker UND rechter) Rand sein -- die Zelle
    wurde dann zweimal gezaehlt, obwohl set_stitch() sie nur einmal
    tatsaechlich veraendert. Pattern 5x3: bei margin=1 ist Zeile 1 sowohl
    top_row als auch bottom_row (height-1-margin = 3-1-1 = 1)."""
    from pysticky.core import Pattern, Thread
    from pysticky.plugins import discover_plugins, run_plugin

    pattern = Pattern(width=5, height=3)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Red", "#FF0000"))

    plugins = {p.id: p for p in discover_plugins()}
    border = plugins["pysticky.border"]

    ctx = MockContext(int_answers=[1, 1])  # margin=1, thickness=1
    run_plugin(border, pattern, ctx)

    layer = pattern.layer_stack.active_layer
    actual_cells = sum(
        1
        for y in range(pattern.height)
        for x in range(pattern.width)
        if layer.get_stitch(x, y) is not None
    )
    assert actual_cells == 3  # Zeile 1, Spalten 1-3

    assert "3 Stiche" in ctx.messages[0]


def test_checkerboard_plugin_fills_pattern(empty_pattern):
    """Schachbrett-Plugin fuellt das gesamte Pattern."""
    from pysticky.core import Thread
    from pysticky.plugins import discover_plugins, run_plugin

    pattern = empty_pattern  # 10x10
    pattern.add_color(Thread.from_hex("Black", "#000000"))
    pattern.add_color(Thread.from_hex("White", "#FFFFFF"))

    plugins = {p.id: p for p in discover_plugins()}
    cb = plugins["pysticky.checkerboard"]

    ctx = MockContext(int_answers=[1])  # cell_size=1
    run_plugin(cb, pattern, ctx)

    layer = pattern.layer_stack.active_layer
    # Bei cell_size=1: (0,0) und (1,1) gleiche Farbe, (0,1) und (1,0) andere
    c00 = layer.get_stitch(0, 0)
    c01 = layer.get_stitch(0, 1)
    c10 = layer.get_stitch(1, 0)
    c11 = layer.get_stitch(1, 1)
    assert c00 == c11
    assert c01 == c10
    assert c00 != c01


def test_checkerboard_plugin_needs_two_colors(empty_pattern):
    """Schachbrett wirft bei <2 Farben einen Fehler."""
    from pysticky.plugins import discover_plugins, run_plugin

    # Default-Black ist bei Pattern, aber nur eine Farbe — wir loeschen sie
    empty_pattern.color_entries.clear()
    plugins = {p.id: p for p in discover_plugins()}
    cb = plugins["pysticky.checkerboard"]

    ctx = MockContext(int_answers=[1])
    run_plugin(cb, empty_pattern, ctx)
    assert any("Schachbrett braucht" in err for err in ctx.errors)


def test_mirror_horizontal_plugin(empty_pattern):
    """Mirror-Horizontal: was links steht, kommt auch rechts gespiegelt an."""
    from pysticky.plugins import discover_plugins, run_plugin

    pattern = empty_pattern  # 10x10 (Default-Black ist drin)
    # Auf der linken Haelfte ein paar Stiche setzen
    pattern.set_stitch(1, 3, 0)
    pattern.set_stitch(2, 5, 0)
    pattern.set_stitch(0, 0, 0)

    plugins = {p.id: p for p in discover_plugins()}
    mirror = plugins["pysticky.mirror_horizontal"]

    ctx = MockContext()
    run_plugin(mirror, pattern, ctx)

    layer = pattern.layer_stack.active_layer
    # width=10 -> width-1-src_x: für src_x=1 -> dst=8, src=2 -> dst=7, src=0 -> dst=9
    assert layer.get_stitch(8, 3) is not None
    assert layer.get_stitch(7, 5) is not None
    assert layer.get_stitch(9, 0) is not None


def test_all_builtin_plugins_have_valid_manifest():
    """Alle built-in Plugin-Manifeste sind parsbar."""
    from pysticky.plugins import discover_plugins

    plugins = discover_plugins()
    for p in plugins:
        assert p.id
        assert p.name
        assert p.manifest.version
