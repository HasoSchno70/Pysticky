"""
Plugin-System für PySticky.

Plugins sind Python-Module, die ein Pattern manipulieren können. Jedes
Plugin liegt in einem eigenen Verzeichnis, das eine `manifest.json` und
ein Python-Modul (z.B. `plugin.py`) enthält.

Suchpfade:
    1. `src/pysticky/plugins/builtin/`  — mitgeliefert
    2. `~/.pysticky/plugins/`           — User-installiert

Manifest-Format (manifest.json):

    {
      "id": "unique_plugin_id",
      "name": "Anzeigename",
      "version": "1.0.0",
      "description": "Was das Plugin macht",
      "entry_module": "plugin",
      "entry_function": "run"
    }

Plugin-Modul-Signatur:

    def run(pattern: Pattern, ctx: PluginContext) -> None:
        ctx.show_message("Hello!")
        # ... Pattern manipulieren ...

`ctx` ist ein PluginContext-Objekt mit:
    - show_message(text: str)
    - show_error(text: str)
    - prompt_int(question: str, default: int = 0, min: int, max: int) -> int | None
    - prompt_str(question: str, default: str = "") -> str | None
    - progress(value: float, text: str = "")   # 0.0..1.0
"""

from .api import (
    Plugin,
    PluginContext,
    PluginError,
    PluginManifest,
    discover_plugins,
    run_plugin,
)

__all__ = [
    "Plugin",
    "PluginContext",
    "PluginError",
    "PluginManifest",
    "discover_plugins",
    "run_plugin",
]
