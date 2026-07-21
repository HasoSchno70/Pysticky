"""
Workspace-Profilverwaltung.

Speichert und stellt Dock-Widget-Layouts (QMainWindow state/geometry) wieder her.
"""

from PySide6.QtCore import QSettings
from PySide6.QtGui import QGuiApplication


class WorkspaceProfileManager:
    """Verwaltet benannte Workspace-Profile über QSettings."""

    PREFIX = "workspace_profiles"

    def __init__(self, settings: QSettings) -> None:
        self._settings = settings

    def list_profiles(self) -> list[str]:
        """Gibt alle gespeicherten Profilnamen zurück."""
        self._settings.beginGroup(self.PREFIX)
        names = self._settings.childGroups()
        self._settings.endGroup()
        return sorted(names)

    def save_profile(self, name: str, main_window) -> None:
        """Speichert den aktuellen Fenster-/Dock-Zustand als Profil."""
        key = f"{self.PREFIX}/{name}"
        self._settings.setValue(f"{key}/state", main_window.saveState())
        self._settings.setValue(f"{key}/geometry", main_window.saveGeometry())

    def load_profile(self, name: str, main_window) -> bool:
        """Stellt ein gespeichertes Profil wieder her."""
        key = f"{self.PREFIX}/{name}"
        state = self._settings.value(f"{key}/state")
        geometry = self._settings.value(f"{key}/geometry")
        if state is None:
            return False
        main_window.restoreState(state)
        if geometry is not None:
            restored_ok = bool(main_window.restoreGeometry(geometry))
            if restored_ok:
                # Gleicher Check wie main_window.py::_setup_window (Runde 7):
                # restoreGeometry() kann erfolgreich sein, obwohl das Ergebnis
                # auf keinem aktuell angeschlossenen Bildschirm mehr sichtbar
                # ist -- z.B. wenn das Profil mit einem zweiten Monitor
                # gespeichert wurde, der inzwischen abgesteckt ist. Ohne
                # diesen Check bliebe das Fenster ausserhalb des sichtbaren
                # Desktops haengen.
                frame = main_window.frameGeometry()
                visible_on_some_screen = any(
                    s.availableGeometry().intersects(frame) for s in QGuiApplication.screens()
                )
                if not visible_on_some_screen:
                    from ..config import UI_CONFIG

                    screen = main_window.screen().availableGeometry()
                    width = min(UI_CONFIG.default_window_width, int(screen.width() * 0.92))
                    height = min(UI_CONFIG.default_window_height, int(screen.height() * 0.92))
                    main_window.resize(width, height)
                    main_window.move(
                        (screen.width() - width) // 2,
                        (screen.height() - height) // 2,
                    )
        return True

    def delete_profile(self, name: str) -> None:
        """Löscht ein Profil."""
        self._settings.beginGroup(f"{self.PREFIX}/{name}")
        self._settings.remove("")
        self._settings.endGroup()

    def has_profile(self, name: str) -> bool:
        """Prüft ob ein Profil existiert."""
        return name in self.list_profiles()
