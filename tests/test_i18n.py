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
    (oder setzt sie, aber Translation faellt durch Identity).

    Regression (Test-Qualitaets-Audit): die vorherige Version pruefte nur
    `isinstance(result, str)` -- das waere auch bei einem kaputten
    Identity-Fallback wahr gewesen (z.B. wenn t() bei unbekannter Sprache
    versehentlich "klingon" selbst, einen leeren String oder sonst
    irgendeinen anderen String zurueckgeben wuerde). Die aktive Sprache
    bleibt "de" (Fixture-Default), also muss t("Speichern") exakt
    "Speichern" liefern -- wie in test_translation_returns_key_in_default_language.
    """
    from pysticky.core.i18n import set_language, t

    set_language("klingon")  # existiert nicht
    # Identity-Fallback ist immer noch da
    result = t("Speichern")
    assert result == "Speichern"


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


def test_language_file_with_invalid_encoding_falls_back_to_identity(tmp_path):
    """Sprachdatei mit ungueltiger UTF-8-Kodierung darf t() nicht mit einem
    rohen UnicodeDecodeError crashen lassen -- soll wie jede andere kaputte
    Sprachdatei auf den Identity-Fallback zurueckfallen."""
    from pysticky.core.i18n import get_translation_manager, set_language, t

    (tmp_path / "xx.json").write_bytes(b'{"Speichern": "Save"}\xff\xfe')

    manager = get_translation_manager()
    original_dir = manager._i18n_dir
    manager._i18n_dir = tmp_path
    manager.reload()
    try:
        set_language("xx")
        assert t("Speichern") == "Speichern"
    finally:
        manager._i18n_dir = original_dir
        manager.reload()


def test_language_file_with_non_dict_root_falls_back_to_identity(tmp_path):
    """Sprachdatei mit syntaktisch gueltigem JSON, das aber kein Objekt ist
    (z.B. eine Liste), darf t() nicht mit einem AttributeError crashen
    lassen -- soll auf den Identity-Fallback zurueckfallen."""
    import json as _json

    from pysticky.core.i18n import get_translation_manager, set_language, t

    (tmp_path / "yy.json").write_text(_json.dumps(["not", "a", "dict"]), encoding="utf-8")

    manager = get_translation_manager()
    original_dir = manager._i18n_dir
    manager._i18n_dir = tmp_path
    manager.reload()
    try:
        set_language("yy")
        assert t("Speichern") == "Speichern"
    finally:
        manager._i18n_dir = original_dir
        manager.reload()


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
