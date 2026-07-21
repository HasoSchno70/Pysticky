# -*- coding: utf-8 -*-
"""Tests fuer die Projekt-Liste (core/project_list.py)."""

from pysticky.core.project_list import ProjectList


def test_add_and_items(tmp_path):
    pl = ProjectList(tmp_path / "projects.json")
    a, b = str(tmp_path / "a.pxs"), str(tmp_path / "b.pxs")
    assert pl.add(a) is True
    assert pl.add(b) is True
    assert pl.items() == [a, b]
    assert len(pl) == 2


def test_add_duplicate_returns_false(tmp_path):
    pl = ProjectList(tmp_path / "projects.json")
    a = str(tmp_path / "a.pxs")
    pl.add(a)
    assert pl.add(a) is False
    assert len(pl) == 1


def test_add_normalizes_relative_vs_absolute_as_same_path(tmp_path, monkeypatch):
    """Regression: add() dedupte frueher per rohem str(Path(path)) ohne
    resolve() -- derselbe Pfad relativ vs. absolut aufgerufen ergab zwei
    Eintraege statt einem (misc_handlers.py::_add_recent_file macht das
    fuer die Zuletzt-geoeffnet-Liste schon richtig, project_list.py war
    nie nachgezogen worden)."""
    monkeypatch.chdir(tmp_path)
    pl = ProjectList(tmp_path / "projects.json")
    assert pl.add("a.pxs") is True
    assert pl.add(str(tmp_path / "a.pxs")) is False  # dieselbe Datei, absoluter Pfad
    assert len(pl) == 1


def test_remove(tmp_path):
    pl = ProjectList(tmp_path / "projects.json")
    a, b = str(tmp_path / "a.pxs"), str(tmp_path / "b.pxs")
    pl.add(a)
    pl.add(b)
    pl.remove(a)
    assert pl.items() == [b]


def test_remove_nonexistent_does_not_raise(tmp_path):
    pl = ProjectList(tmp_path / "projects.json")
    pl.remove("does_not_exist.pxs")
    assert len(pl) == 0


def test_save_and_reload(tmp_path):
    path = tmp_path / "projects.json"
    a, b = str(tmp_path / "a.pxs"), str(tmp_path / "b.pxs")
    pl1 = ProjectList(path)
    pl1.add(a)
    pl1.add(b)
    pl1.save()

    assert path.exists()
    pl2 = ProjectList(path)
    assert pl2.items() == [a, b]


def test_load_corrupt_file_does_not_crash(tmp_path):
    path = tmp_path / "projects.json"
    path.write_text("{ not valid json", encoding="utf-8")
    pl = ProjectList(path)
    assert len(pl) == 0


def test_load_missing_file_is_empty(tmp_path):
    pl = ProjectList(tmp_path / "does_not_exist.json")
    assert len(pl) == 0
