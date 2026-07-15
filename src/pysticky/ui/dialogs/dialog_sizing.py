"""
Gemeinsame Auto-Groessen-Logik fuer Dialoge mit variabel grossem Inhalt
(Tabs, Sektionen, ...).

Ohne dies muessten Dialoge auf eine feste Default-Groesse geraten, die fuer
den groessten Inhalt (laengste Tab-Seite, meiste Sektionen, ...) oft zu klein
ist -- der Inhalt landet dann in einer internen QScrollArea, obwohl der
Dialog selbst noch reichlich Bildschirmplatz haette. `auto_size_dialog`
bemisst die Dialoggroesse stattdessen am tatsaechlichen `sizeHint()` des
Inhalts, begrenzt auf einen Anteil der verfuegbaren Bildschirmflaeche (damit
der Dialog auf kleinen/anderen Monitoren nicht ueber den Rand waechst -- eine
QScrollArea um den Inhalt bleibt dafuer als Fallback sinnvoll).
"""

from PySide6.QtWidgets import QApplication, QDialog, QWidget


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
    """Passt `dialog` an den tatsaechlichen Platzbedarf seines Inhalts an.

    Args:
        dialog: der zu vergroessernde Dialog.
        content_widgets: Widgets, deren sizeHint() den Platzbedarf bestimmt
            (z.B. alle Tab-Seiten eines QTabWidget, oder eine Liste mit nur
            dem einen Hauptinhalts-Widget bei tabelosen Dialogen). Es wird
            jeweils das Maximum ueber Breite/Hoehe genommen — passend fuer
            Tabs, von denen immer nur einer sichtbar ist. Wird ignoriert,
            wenn `content_size` gesetzt ist.
        min_width: zusaetzliche Mindestbreite, die unabhaengig vom Inhalt
            erreicht werden soll (z.B. die Breite einer Tab-Leiste, die
            schmaler Inhalt sonst unterschreiten wuerde).
        chrome_w/chrome_h: Platz fuer Rahmen, Buttons, Abstaende etc., der
            zum reinen Inhalts-sizeHint hinzukommt.
        max_width_frac/max_height_frac: Obergrenze als Anteil der
            verfuegbaren Bildschirmflaeche.
        content_size: (Breite, Hoehe) direkt vorgeben statt aus
            `content_widgets` per max() abzuleiten — noetig, wenn mehrere
            Bereiche gleichzeitig sichtbar sind (z.B. nebeneinander- oder
            untereinandergestapelte Sektionen), wo sich die Groessen
            addieren statt dass nur die groesste zaehlt.
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

    dialog.resize(max(target_w, dialog.minimumWidth()), max(target_h, dialog.minimumHeight()))
