"""
Hintergrund-Worker für den Bildimport.
"""

from PySide6.QtCore import QObject, Signal

from ....core import ImportSettings, import_image


class _ImageImportWorker(QObject):
    """Worker für Hintergrund-Bildimport."""

    finished = Signal(object)  # Pattern oder None
    error = Signal(str)

    def __init__(self, image_path: str, settings: "ImportSettings", crop: tuple | None) -> None:
        super().__init__()
        self._image_path = image_path
        self._settings = settings
        self._crop = crop

    def run(self) -> None:
        """Führt den Import im Hintergrund aus."""
        try:
            pattern = import_image(self._image_path, self._settings, self._crop)
            self.finished.emit(pattern)
        except (OSError, ValueError) as e:
            self.error.emit(str(e))
