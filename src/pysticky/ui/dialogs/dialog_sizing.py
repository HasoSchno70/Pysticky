"""
Gemeinsame Auto-Größen-Logik für Dialoge mit variabel grossem Inhalt
(Tabs, Sektionen, ...).

Ohne dies müssten Dialoge auf eine feste Default-Größe geraten, die für
den größten Inhalt (längste Tab-Seite, meiste Sektionen, ...) oft zu klein
ist -- der Inhalt landet dann in einer internen QScrollArea, obwohl der
Dialog selbst noch reichlich Bildschirmplatz hätte. `auto_size_dialog`
bemisst die Dialoggröße stattdessen am tatsächlichen `sizeHint()` des
Inhalts, begrenzt auf einen Anteil der verfügbaren Bildschirmfläche (damit
der Dialog auf kleinen/anderen Monitoren nicht über den Rand wächst -- eine
QScrollArea um den Inhalt bleibt dafür als Fallback sinnvoll).
"""

import os

from PySide6.QtWidgets import QApplication, QDialog, QWidget

_DEBUG_ENV_VAR = "PYSTICKY_DEBUG_DIALOG_SIZING"


def auto_size_dialog(
    dialog: QDialog,
    content_widgets: list[QWidget],
    *,
    min_width: int = 0,
    chrome_w: int = 60,
    chrome_h: int = 150,
    max_width_frac: float = 0.9,
    max_height_frac: float = 0.92,
    content_size: tuple[int, int] | None = None,
) -> None:
    """Passt `dialog` an den tatsächlichen Platzbedarf seines Inhalts an.

    Args:
        dialog: der zu vergrößernde Dialog.
        content_widgets: Widgets, deren sizeHint() den Platzbedarf bestimmt
            (z.B. alle Tab-Seiten eines QTabWidget, oder eine Liste mit nur
            dem einen Hauptinhalts-Widget bei tabelosen Dialogen). Es wird
            jeweils das Maximum über Breite/Höhe genommen — passend für
            Tabs, von denen immer nur einer sichtbar ist. Wird ignoriert,
            wenn `content_size` gesetzt ist.
        min_width: zusätzliche Mindestbreite, die unabhängig vom Inhalt
            erreicht werden soll (z.B. die Breite einer Tab-Leiste, die
            schmaler Inhalt sonst unterschreiten würde).
        chrome_w/chrome_h: Platz für Rahmen, Buttons, Abstände etc., der
            zum reinen Inhalts-sizeHint hinzukommt.
        max_width_frac/max_height_frac: Obergrenze als Anteil der
            verfügbaren Bildschirmfläche.
        content_size: (Breite, Höhe) direkt vorgeben statt aus
            `content_widgets` per max() abzuleiten — nötig, wenn mehrere
            Bereiche gleichzeitig sichtbar sind (z.B. nebeneinander- oder
            untereinandergestapelte Sektionen), wo sich die Größen
            addieren statt dass nur die größte zählt.
    """
    if content_size is not None:
        content_w, content_h = content_size
    else:
        content_w = max((w.sizeHint().width() for w in content_widgets), default=0)
        content_h = max((w.sizeHint().height() for w in content_widgets), default=0)

    target_w = max(content_w + chrome_w, min_width)
    target_h = content_h + chrome_h

    screen = dialog.screen() or QApplication.primaryScreen()
    avail = screen.availableGeometry() if screen else None
    if avail is not None:
        target_w = min(target_w, int(avail.width() * max_width_frac))
        target_h = min(target_h, int(avail.height() * max_height_frac))

    # min_width ist eine harte Anforderung (z.B. "Tab-Leiste passt sonst
    # nicht") -- die Bildschirm-Kappung oben darf sie nicht mehr unterbieten.
    # Lieber etwas breiter als der empfohlene Bildschirmanteil als eine
    # abgeschnittene Tab-Leiste.
    target_w = max(target_w, min_width)

    final_w = max(target_w, dialog.minimumWidth())
    final_h = max(target_h, dialog.minimumHeight())

    if os.environ.get(_DEBUG_ENV_VAR):
        _debug_print(
            dialog,
            screen,
            avail,
            content_w,
            content_h,
            min_width,
            target_w,
            target_h,
            final_w,
            final_h,
        )

    dialog.resize(final_w, final_h)


def _debug_print(
    dialog, screen, avail, content_w, content_h, min_width, target_w, target_h, final_w, final_h
):
    """Gibt jeden Zwischenschritt der Größenberechnung aus. Aktiviert per
    Umgebungsvariable PYSTICKY_DEBUG_DIALOG_SIZING=1 -- gedacht, um auf einer
    Maschine, die mit Headless-Tests nicht reproduzierbare Truncation zeigt,
    einmalig echte Bildschirm-/DPI-Werte aus einem realen (nicht-offscreen)
    Lauf einzusammeln (siehe open-items.md zum PatternStatisticsDialog)."""
    name = type(dialog).__name__
    print(f"[dialog_sizing] {name}: content={content_w}x{content_h} min_width={min_width}")
    if screen is not None:
        geo = screen.geometry()
        print(
            f"[dialog_sizing] {name}: screen={screen.name()!r} "
            f"dpr={screen.devicePixelRatio()} logicalDPI={screen.logicalDotsPerInch()} "
            f"geometry={geo.width()}x{geo.height()}"
        )
    else:
        print(f"[dialog_sizing] {name}: screen=None (weder dialog.screen() noch primaryScreen())")
    if avail is not None:
        print(f"[dialog_sizing] {name}: availableGeometry={avail.width()}x{avail.height()}")
    else:
        print(f"[dialog_sizing] {name}: availableGeometry=None")
    print(
        f"[dialog_sizing] {name}: target={target_w}x{target_h} "
        f"dialog.minimumSize={dialog.minimumWidth()}x{dialog.minimumHeight()} "
        f"final={final_w}x{final_h}"
    )
