"""
Bildimport-Dialog als Package.

Der Dialog ist nach dem hauseigenen Mixin-Muster (siehe ``ui/builders/``,
``ui/handlers/`` und ``ui/canvas/mixins/``) auf mehrere Module verteilt:
eine Klasse zur Laufzeit, Verantwortungen pro Datei.
"""

from .dialog import ImageImportDialog

__all__ = ["ImageImportDialog"]
