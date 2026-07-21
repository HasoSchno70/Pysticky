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
        except Exception as e:  # noqa: BLE001 - siehe unten
            # Ohne diesen Catch-all haette JEDER unerwartete Fehler (z.B.
            # PIL.Image.DecompressionBombError bei einem riesigen Quellbild,
            # oder ein interner Fehler in der Dithering-/Quantisierungs-
            # Pipeline) weder finished noch error feuern lassen -- der
            # QThread waere nie fertig geworden und der modale
            # Fortschrittsdialog (dialog.py::_on_import()) haette sich
            # dauerhaft nicht mehr schliessen lassen (_import_running()
            # bleibt True, solange der Thread laeuft). Gleiche Bug-Klasse
            # wie bei oxs_io.py in Runde 11.
            self.error.emit(str(e))
