# -*- coding: utf-8 -*-
"""Regressionstests für pysticky.utils.os_open.

`os.startfile()` gibt es nur unter Windows; `xdg-open` ist ein
Linux-Kommando und existiert auf macOS nicht. Diese Tests stellen
sicher, dass open_path()/reveal_in_file_manager() auf JEDER der drei
Plattformen das richtige Kommando waehlen -- insbesondere, dass macOS
("Darwin") nicht mehr faelschlich in den Linux-Zweig (xdg-open) faellt,
wo es lautlos fehlschlagen wuerde (Kommando nicht gefunden).

Da dieser Test auf einer Windows-Maschine laeuft, wird die tatsaechliche
Plattform ueber `platform.system` gemockt -- getestet wird die
Verzweigungs-LOGIK, nicht der reale Aufruf auf einem echten Linux/macOS.
"""

from pathlib import Path
from unittest.mock import patch

from pysticky.utils import os_open


class TestOpenPath:
    def test_windows_uses_startfile(self) -> None:
        with (
            patch.object(os_open.platform, "system", return_value="Windows"),
            patch.object(os_open.os, "startfile", create=True) as mock_startfile,
            patch.object(os_open.subprocess, "run") as mock_run,
        ):
            os_open.open_path("C:/some/file.pdf")

        mock_startfile.assert_called_once_with("C:/some/file.pdf")
        mock_run.assert_not_called()

    def test_macos_uses_open_not_xdg_open(self) -> None:
        """Regression: vorher fiel macOS in den 'else'-Zweig (xdg-open),
        das Kommando existiert auf macOS nicht -> stiller Fehlschlag."""
        with (
            patch.object(os_open.platform, "system", return_value="Darwin"),
            patch.object(os_open.subprocess, "run") as mock_run,
        ):
            os_open.open_path("/some/file.pdf")

        mock_run.assert_called_once_with(["open", "/some/file.pdf"])
        # Sicherstellen, dass wirklich "open" und nicht "xdg-open" gewaehlt wurde.
        called_args = mock_run.call_args[0][0]
        assert "xdg-open" not in called_args

    def test_linux_uses_xdg_open(self) -> None:
        with (
            patch.object(os_open.platform, "system", return_value="Linux"),
            patch.object(os_open.subprocess, "run") as mock_run,
        ):
            os_open.open_path("/some/file.pdf")

        mock_run.assert_called_once_with(["xdg-open", "/some/file.pdf"])


class TestRevealInFileManager:
    def test_windows_uses_explorer_select(self) -> None:
        with (
            patch.object(os_open.platform, "system", return_value="Windows"),
            patch.object(os_open.subprocess, "run") as mock_run,
        ):
            os_open.reveal_in_file_manager("C:/some/file.pxs")

        mock_run.assert_called_once_with(["explorer", "/select,", "C:/some/file.pxs"])

    def test_macos_uses_open_reveal_flag(self) -> None:
        """Regression: vorher fiel macOS auf xdg-open zurueck (existiert
        auf macOS nicht) statt auf 'open -R' (Datei im Finder anzeigen)."""
        with (
            patch.object(os_open.platform, "system", return_value="Darwin"),
            patch.object(os_open.subprocess, "run") as mock_run,
        ):
            os_open.reveal_in_file_manager("/some/file.pxs")

        mock_run.assert_called_once_with(["open", "-R", "/some/file.pxs"])

    def test_linux_falls_back_to_parent_folder(self) -> None:
        with (
            patch.object(os_open.platform, "system", return_value="Linux"),
            patch.object(os_open.subprocess, "run") as mock_run,
        ):
            os_open.reveal_in_file_manager("/some/dir/file.pxs")

        expected_parent = str(Path("/some/dir/file.pxs").parent)
        mock_run.assert_called_once_with(["xdg-open", expected_parent])
