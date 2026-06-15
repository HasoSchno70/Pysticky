"""
Benachrichtigungs-Scopes für Panel-Updates.
"""


class NotifyScope:
    """Benachrichtigungs-Scopes für Panel-Updates.

    Einzelne Scopes:
        STITCH   – Stich-Daten geändert (info, color_bar, status)
        VISUAL   – Canvas/Minimap/Tile neu zeichnen
        PALETTE  – Farbpalette geändert
        PROGRESS – Fortschritts-Tracking
        FULL     – Alles (neues Pattern geladen)

    Kombinationen (Tupel):
        STITCH_VISUAL  – Stich + visuelles Refresh (z.B. Undo/Redo)
    """

    STITCH = "stitch"
    VISUAL = "visual"
    PALETTE = "palette"
    PROGRESS = "progress"
    FULL = "full"
    # Häufige Kombinationen
    STITCH_VISUAL = ("stitch", "visual")
