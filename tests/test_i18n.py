# -*- coding: utf-8 -*-
"""Tests fuer die i18n-Infrastructure."""

import pytest


@pytest.fixture(autouse=True)
def _reset_language():
    """Vor und nach jedem Test: Sprache zurueck auf de (Default)."""
    from pysticky.core.i18n import get_translation_manager, set_language

    set_language("de")
    yield
    set_language("de")
    # Cache leeren, damit Tests bei Aenderungen an JSON neu laden
    get_translation_manager().reload()


def test_available_languages_finds_de_and_en():
    """Default-Discovery findet die mitgelieferten Sprachen."""
    from pysticky.core.i18n import available_languages

    langs = available_languages()
    assert "de" in langs
    assert "en" in langs


def test_default_language_is_de():
    """Initial-Sprache ist deutsch."""
    from pysticky.core.i18n import current_language

    assert current_language() == "de"


def test_translation_returns_key_in_default_language():
    """In deutscher Sprache wird der Key selbst zurueckgegeben (Identity)."""
    from pysticky.core.i18n import t

    assert t("Speichern") == "Speichern"
    assert t("Anything goes") == "Anything goes"


def test_set_language_switches_to_english():
    """Sprache umschalten und Englisch zurueckkriegen."""
    from pysticky.core.i18n import set_language, t

    set_language("en")
    assert t("Speichern") == "Save"
    assert t("&Datei") == "&File"


def test_unknown_key_falls_back_to_key_in_english():
    """Unbekannter Key liefert den Key selbst (kein Crash, keine None)."""
    from pysticky.core.i18n import set_language, t

    set_language("en")
    result = t("Dieser String existiert garantiert nicht xyzzy")
    assert result == "Dieser String existiert garantiert nicht xyzzy"


def test_switching_back_to_german_restores_keys():
    """Hin und zurueck schalten."""
    from pysticky.core.i18n import set_language, t

    set_language("en")
    assert t("Speichern") == "Save"
    set_language("de")
    assert t("Speichern") == "Speichern"


def test_unknown_language_does_nothing_to_translations():
    """set_language mit unbekannter Sprache: Manager bleibt bei aktueller Sprache
    (oder setzt sie, aber Translation faellt durch Identity)."""
    from pysticky.core.i18n import set_language, t

    set_language("klingon")  # existiert nicht
    # Identity-Fallback ist immer noch da
    result = t("Speichern")
    assert isinstance(result, str)


def test_current_language_reports_active():
    """current_language gibt die zuletzt gesetzte Sprache zurueck."""
    from pysticky.core.i18n import current_language, set_language

    set_language("en")
    assert current_language() == "en"


def test_singleton_returns_same_manager():
    """get_translation_manager() ist Singleton."""
    from pysticky.core.i18n import get_translation_manager

    a = get_translation_manager()
    b = get_translation_manager()
    assert a is b


def test_translation_persists_across_calls():
    """Mehrere Translate-Aufrufe sind stabil."""
    from pysticky.core.i18n import set_language, t

    set_language("en")
    a = t("Speichern")
    b = t("Speichern")
    assert a == b == "Save"


def test_english_translation_loads_meta_fields():
    """en.json hat _meta_language_name."""
    from pysticky.core.i18n import set_language, t

    set_language("en")
    assert t("_meta_language_name") == "English"


def test_translation_handles_special_characters():
    """Strings mit Umlauten und Sonderzeichen funktionieren."""
    from pysticky.core.i18n import set_language, t

    set_language("en")
    # Mehrere Strings mit Umlauten
    assert t("&Öffnen...") == "&Open..."
    assert t("Größe:") == "Size:"
    assert t("Schließen") == "Close"


def test_threadsafe_concurrent_access():
    """Mehrere Threads koennen gleichzeitig t() rufen ohne Crash."""
    import threading

    from pysticky.core.i18n import set_language, t

    set_language("en")
    results: list[str] = []

    def worker():
        for _ in range(100):
            results.append(t("Speichern"))

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for tt in threads:
        tt.start()
    for tt in threads:
        tt.join()

    assert all(r == "Save" for r in results)
    assert len(results) == 500
