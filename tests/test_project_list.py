# -*- coding: utf-8 -*-
"""Tests fuer die Projekt-Liste (core/project_list.py)."""

from pysticky.core.project_list import ProjectList


def test_add_and_items(tmp_path):
    pl = ProjectList(tmp_path / "projects.json")
    assert pl.add("a.pxs") is True
    assert pl.add("b.pxs") is True
    assert pl.items() == ["a.pxs", "b.pxs"]
    assert len(pl) == 2


def test_add_duplicate_returns_false(tmp_path):
    pl = ProjectList(tmp_path / "projects.json")
    pl.add("a.pxs")
    assert pl.add("a.pxs") is False
    assert len(pl) == 1


def test_remove(tmp_path):
    pl = ProjectList(tmp_path / "projects.json")
    pl.add("a.pxs")
    pl.add("b.pxs")
    pl.remove("a.pxs")
    assert pl.items() == ["b.pxs"]


def test_remove_nonexistent_does_not_raise(tmp_path):
    pl = ProjectList(tmp_path / "projects.json")
    pl.remove("does_not_exist.pxs")
    assert len(pl) == 0


def test_save_and_reload(tmp_path):
    path = tmp_path / "projects.json"
    pl1 = ProjectList(path)
    pl1.add("a.pxs")
    pl1.add("b.pxs")
    pl1.save()

    assert path.exists()
    pl2 = ProjectList(path)
    assert pl2.items() == ["a.pxs", "b.pxs"]


def test_load_corrupt_file_does_not_crash(tmp_path):
    path = tmp_path / "projects.json"
    path.write_text("{ not valid json", encoding="utf-8")
    pl = ProjectList(path)
    assert len(pl) == 0


def test_load_missing_file_is_empty(tmp_path):
    pl = ProjectList(tmp_path / "does_not_exist.json")
    assert len(pl) == 0
