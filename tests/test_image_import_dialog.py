# -*- coding: utf-8 -*-
"""Tests für "Bildimport wiederholen" (Wizard Recall) -- Vorbefüllen des
Import-Dialogs aus einem bereits importierten Pattern."""

import pytest
from PIL import Image
from PySide6.QtWidgets import QMessageBox

from pysticky.core import Pattern
from pysticky.core.image_import import ImportSettings, import_image
from pysticky.ui.dialogs import ImageImportDialog


@pytest.fixture
def source_image_path(tmp_path):
    path = tmp_path / "quelle.png"
    Image.new("RGB", (40, 20), (200, 100, 50)).save(path)
    return path


@pytest.fixture
def seeded_pattern(source_image_path):
    """Pattern, wie es ein echter Bildimport erzeugen würde -- mit allen
    source_*/metadata-Feldern, die die Recall-Funktion ausliest."""
    settings = ImportSettings(
        width=16,
        height=12,
        max_colors=12,
        palette_name="DMC",
        dithering_mode="floyd_steinberg",
        quantization_method="median_cut",
        keep_aspect_ratio=False,
        auto_backstitches=True,
        brightness=1.3,
        contrast=0.7,
        saturation=1.4,
        confetti_min_run_size=3,
    )
    return import_image(source_image_path, settings, crop=(0.1, 0.2, 0.9, 0.8))


def test_seed_from_pattern_restores_path_and_size(qtbot, seeded_pattern, source_image_path):
    dlg = ImageImportDialog(seed_pattern=seeded_pattern)
    qtbot.addWidget(dlg)

    assert dlg._image_path == source_image_path
    assert dlg.spin_width.value() == 16
    assert dlg.spin_height.value() == 12


def test_seed_from_pattern_restores_crop(qtbot, seeded_pattern):
    dlg = ImageImportDialog(seed_pattern=seeded_pattern)
    qtbot.addWidget(dlg)

    assert dlg.crop_preview.get_crop() == pytest.approx((0.1, 0.2, 0.9, 0.8))
    assert dlg.btn_reset_crop.isEnabled()


def test_seed_from_pattern_restores_palette_and_settings(qtbot, seeded_pattern):
    dlg = ImageImportDialog(seed_pattern=seeded_pattern)
    qtbot.addWidget(dlg)

    assert dlg.combo_palette.currentText() == "DMC"
    assert dlg.spin_colors.value() == 12
    assert dlg.combo_dithering.currentIndex() == 1  # floyd_steinberg
    assert dlg.combo_quantization.currentIndex() == 1  # median_cut
    assert dlg.chk_backstitches.isChecked() is True
    assert dlg.chk_aspect.isChecked() is False
    assert dlg.spin_confetti.value() == 3


def test_seed_from_pattern_restores_image_adjustments(qtbot, seeded_pattern):
    dlg = ImageImportDialog(seed_pattern=seeded_pattern)
    qtbot.addWidget(dlg)

    assert dlg.slider_brightness.value() == 130
    assert dlg.slider_contrast.value() == 70
    assert dlg.slider_saturation.value() == 140


def test_seed_from_pattern_reproduces_settings_object(qtbot, seeded_pattern):
    """End-to-End: die aus den vorbefüllten Widgets abgeleiteten
    ImportSettings müssen den Original-Settings entsprechen -- das ist der
    eigentliche Zweck von Wizard Recall (identisch wiederholbarer Import)."""
    dlg = ImageImportDialog(seed_pattern=seeded_pattern)
    qtbot.addWidget(dlg)

    settings = dlg._get_settings()
    assert settings.width == 16
    assert settings.height == 12
    assert settings.max_colors == 12
    assert settings.palette_name == "DMC"
    assert settings.dithering_mode == "floyd_steinberg"
    assert settings.quantization_method == "median_cut"
    assert settings.keep_aspect_ratio is False
    assert settings.auto_backstitches is True
    assert settings.brightness == pytest.approx(1.3)
    assert settings.contrast == pytest.approx(0.7)
    assert settings.saturation == pytest.approx(1.4)
    assert settings.confetti_min_run_size == 3


def test_repeated_reimport_updates_metadata_each_time(qtbot, source_image_path):
    """ "Bildimport wiederholen" mehrfach hintereinander mit jeweils
    geaenderten Einstellungen ausgefuehrt -- die metadata-Felder des
    resultierenden Patterns muessen JEDES Mal die zuletzt gewaehlten
    Werte tragen, nicht die vom allerersten Import eingefrorenen (jeder
    import_image()-Aufruf baut sein metadata-Dict frisch aus den
    uebergebenen ImportSettings, siehe core/image_import.py)."""
    settings_v1 = ImportSettings(width=16, height=12, max_colors=12, confetti_min_run_size=1)
    pattern_v1 = import_image(source_image_path, settings_v1, crop=(0, 0, 1, 1))
    assert pattern_v1.metadata["max_colors"] == 12
    assert pattern_v1.metadata["confetti_min_run_size"] == 1

    # Reimport 1: aus pattern_v1 vorbefuellter Dialog, max_colors geaendert
    dlg1 = ImageImportDialog(seed_pattern=pattern_v1)
    qtbot.addWidget(dlg1)
    assert dlg1.spin_colors.value() == 12  # aus pattern_v1 uebernommen
    dlg1.spin_colors.setValue(20)
    dlg1.spin_confetti.setValue(3)
    settings_v2 = dlg1._get_settings()
    pattern_v2 = import_image(source_image_path, settings_v2, crop=dlg1._crop)
    assert pattern_v2.metadata["max_colors"] == 20
    assert pattern_v2.metadata["confetti_min_run_size"] == 3

    # Reimport 2: aus pattern_v2 vorbefuellter Dialog -- muss v2-Werte
    # zeigen, nicht auf v1 zurueckfallen.
    dlg2 = ImageImportDialog(seed_pattern=pattern_v2)
    qtbot.addWidget(dlg2)
    assert dlg2.spin_colors.value() == 20
    assert dlg2.spin_confetti.value() == 3


def test_seed_from_pattern_diamond_mode_reselects_diamond_palette(qtbot, source_image_path):
    """Ein Diamond-Painting-Muster (mode="diamond") wiederholt importieren
    muss wieder eine DP-Palette vorauswaehlen -- nicht nur beim allerersten
    Bildimport (siehe diamond-symbol-consistency-2026-07.md), sondern auch
    beim WIEDERHOLTEN Import ueber Wizard Recall. Die Palette kommt hier
    aus pattern.source_palette_name (in _seed_from_pattern gesetzt), die
    exakte gleiche DP-Palette wie beim urspruenglichen Import muss also
    stabil erhalten bleiben."""
    settings = ImportSettings(width=8, height=6, max_colors=8, palette_name="DMC Diamond Painting")
    pattern = import_image(source_image_path, settings, crop=(0, 0, 1, 1))
    assert pattern.mode == "diamond"
    assert pattern.source_palette_name == "DMC Diamond Painting"

    dlg = ImageImportDialog(prefer_diamond=True, seed_pattern=pattern)
    qtbot.addWidget(dlg)

    assert dlg.combo_palette.currentText() == "DMC Diamond Painting"


def test_seed_from_pattern_without_source_image_stays_blank(qtbot):
    """Pattern ohne source_image_path (z.B. von Hand gezeichnet) -- der
    Dialog darf nicht crashen und bleibt einfach leer."""
    pattern = Pattern(name="Handgezeichnet", width=10, height=10)
    dlg = ImageImportDialog(seed_pattern=pattern)
    qtbot.addWidget(dlg)

    assert dlg._image_path is None
    assert not dlg.btn_import.isEnabled()


def test_seed_from_pattern_with_missing_source_file_stays_blank(qtbot, tmp_path, monkeypatch):
    """Quellbild existiert nicht mehr auf der Platte -- Dialog fängt das
    ab statt zu crashen (gleiche Fehlerbehandlung wie beim manuellen
    Bild-Browsen einer kaputten Datei)."""
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)

    pattern = Pattern(name="Verwaist", width=10, height=10)
    pattern.source_image_path = str(tmp_path / "nicht_mehr_da.png")

    dlg = ImageImportDialog(seed_pattern=pattern)
    qtbot.addWidget(dlg)

    assert dlg._image_path is None


def test_load_image_handles_decompression_bomb_error(qtbot, tmp_path, monkeypatch):
    """get_image_info() -> PIL.Image.open() wirft bei einem sehr grossen
    (aber technisch validen) Bild ein PIL.Image.DecompressionBombError --
    eine normale Exception, KEIN OSError. Der schmale `except OSError` in
    _load_image_from_path() fing das vorher nicht ab: die Exception blieb
    unbehandelt und der Dialog blieb mit self._image_path auf ein nie
    tatsaechlich geladenes Bild zeigend haengen, statt sauber auf None
    zurueckzusetzen und eine Fehlermeldung zu zeigen."""
    warnings_shown = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings_shown.append(a) or None)
    # MAX_IMAGE_PIXELS kuenstlich sehr klein setzen, damit ein normales
    # kleines Testbild bereits die Decompression-Bomb-Schwelle ueberschreitet
    # -- ohne dafuer ein echtes riesiges Bild erzeugen zu muessen.
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 10)

    path = tmp_path / "bild.png"
    Image.new("RGB", (50, 50), (10, 20, 30)).save(path)

    dlg = ImageImportDialog()
    qtbot.addWidget(dlg)

    dlg._load_image_from_path(str(path))

    assert dlg._image_path is None
    assert dlg._image_width == 0
    assert dlg._image_height == 0
    assert len(warnings_shown) == 1
