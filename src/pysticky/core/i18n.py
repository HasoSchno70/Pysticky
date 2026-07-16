"""
Internationalisierung (i18n) für PySticky.

Design-Entscheidung: Statt Qt Linguist (.ts/.qm) nutzen wir eine simple
JSON-Dictionary-basierte Lookup-Funktion `t(key)`. Vorteile:

- Live-reload möglich (kein .qm-Kompilieren nötig)
- Python-idiomatisch — JSON ist einfach zu editieren
- Keine Build-Step-Abhängigkeit
- Identity-Fallback: Wenn ein Key in der Ziel-Sprache fehlt, wird der Key
  selbst zurückgegeben (= deutsche Originalstring), so dass die App auch
  bei unvollständiger Übersetzung lauffähig bleibt.

Verwendung im UI-Code:

    from pysticky.core.i18n import t

    self.setWindowTitle(t("Muster speichern"))

Wenn die aktive Sprache 'de' ist (Default), passiert nichts — der Key
selbst wird geliefert. Wenn 'en' aktiv ist, wird in en.json nachgeschlagen
und der englische Text geliefert.

Sprachen werden aus `resources/i18n/<lang>.json` geladen. Eine Datei muss
NICHT alle Keys enthalten — fehlende Keys fallen auf den Key (deutscher
Originalstring) zurück.
"""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

from ..utils.logging import get_logger

logger = get_logger(__name__)


def _resolve_i18n_dir() -> Path:
    """Findet das resources/i18n-Verzeichnis.

    Im Dev-Mode liegt es relativ zur Quelldatei. In einem PyInstaller-Build
    werden Daten in einen temporären Pfad (sys._MEIPASS) entpackt.
    Wir probieren beide.
    """
    # Dev-Mode-Pfad: src/pysticky/resources/i18n
    dev_path = Path(__file__).parent.parent / "resources" / "i18n"
    if dev_path.exists():
        return dev_path

    # PyInstaller-Frozen: sys._MEIPASS / pysticky/resources/i18n
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        frozen_path = Path(meipass) / "pysticky" / "resources" / "i18n"
        if frozen_path.exists():
            return frozen_path

    # Fallback (existiert nicht — Loader wird leere Dicts liefern)
    return dev_path


class TranslationManager:
    """
    Singleton, der die aktive Sprache und alle geladenen Dictionaries hält.

    Thread-sicher per RLock — Sprachwechsel kann aus dem UI-Thread kommen,
    während Render-Threads `t()` aufrufen.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._current_lang: str = "de"
        self._translations: dict[str, dict[str, str]] = {}
        self._i18n_dir: Path = _resolve_i18n_dir()
        self._available_languages: list[str] = []
        self._discovered = False

    def discover(self) -> list[str]:
        """Findet verfügbare Sprachen (eine pro .json-Datei in resources/i18n/)."""
        with self._lock:
            if self._discovered:
                return list(self._available_languages)
            self._available_languages = []
            if self._i18n_dir.exists():
                for f in sorted(self._i18n_dir.glob("*.json")):
                    self._available_languages.append(f.stem)
            self._discovered = True
            return list(self._available_languages)

    def set_language(self, lang: str) -> None:
        """Schaltet die aktive Sprache um. Lädt das Dictionary lazy."""
        with self._lock:
            if lang == self._current_lang:
                return
            self._ensure_loaded(lang)
            self._current_lang = lang

    @property
    def current_language(self) -> str:
        with self._lock:
            return self._current_lang

    def available_languages(self) -> list[str]:
        return self.discover()

    def translate(self, key: str) -> str:
        """
        Liefert die Übersetzung für `key` in der aktiven Sprache.

        Falls die Sprache 'de' ist ODER kein Eintrag existiert, wird der
        Key selbst zurückgegeben. So bleibt die App auch ohne aktive
        Übersetzung lesbar.
        """
        with self._lock:
            if self._current_lang == "de":
                return key
            self._ensure_loaded(self._current_lang)
            dictionary = self._translations.get(self._current_lang, {})
            return dictionary.get(key, key)

    def _ensure_loaded(self, lang: str) -> None:
        """Lädt die Sprache <lang> wenn noch nicht geladen."""
        if lang in self._translations:
            return
        path = self._i18n_dir / f"{lang}.json"
        if not path.exists():
            logger.warning(f"Sprachdatei nicht gefunden: {path}")
            self._translations[lang] = {}
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._translations[lang] = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Fehler beim Laden von {path}: {e}")
            self._translations[lang] = {}

    def reload(self) -> None:
        """Setzt alle geladenen Dictionaries zurück (für Live-Reload bei Dev)."""
        with self._lock:
            self._translations.clear()
            self._discovered = False


# Singleton
_manager = TranslationManager()


def get_translation_manager() -> TranslationManager:
    """Liefert den globalen TranslationManager."""
    return _manager


def t(key: str) -> str:
    """
    Convenience-Wrapper: liefert die Übersetzung für `key`.

    Idiom:
        from pysticky.core.i18n import t
        self.btn_save.setText(t("Speichern"))
    """
    return _manager.translate(key)


def set_language(lang: str) -> None:
    """Convenience: schaltet die aktive Sprache um."""
    _manager.set_language(lang)


def current_language() -> str:
    """Convenience: liefert die aktuelle Sprache."""
    return _manager.current_language


def available_languages() -> list[str]:
    """Convenience: liefert alle verfügbaren Sprachen."""
    return _manager.available_languages()
