"""
Workspace-Profilverwaltung.

Speichert und stellt Dock-Widget-Layouts (QMainWindow state/geometry) wieder her.
"""

from PySide6.QtCore import QSettings


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
            main_window.restoreGeometry(geometry)
        return True

    def delete_profile(self, name: str) -> None:
        """Löscht ein Profil."""
        self._settings.beginGroup(f"{self.PREFIX}/{name}")
        self._settings.remove("")
        self._settings.endGroup()

    def has_profile(self, name: str) -> bool:
        """Prüft ob ein Profil existiert."""
        return name in self.list_profiles()
