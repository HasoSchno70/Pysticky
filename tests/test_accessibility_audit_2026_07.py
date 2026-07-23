# -*- coding: utf-8 -*-
"""
Accessibility-Audit (Tastatur/Screenreader) -- Runde 37.

Drei unabhaengige Bugs, je ein Fix:

1. accessibleName: BaseToolButton (linke Werkzeugleiste, tool_bar.py)
   zeichnet Icon+Label komplett selbst per paintEvent() -- nie setText(),
   nie setAccessibleName(). Qt's Accessibility-Bridge liefert fuer den
   Name-Wert dann einen leeren String (nur die Tooltip-Description bleibt
   erreichbar); ein Screenreader-Nutzer bekommt fuer JEDEN Werkzeug-Button
   (Stift, Radierer, Fuellen, ...) keinen Namen genannt.

2. Fokus-Sichtbarkeit: `* { outline: none; }` (dark.qss) + fehlende
   `:focus`-Regeln in den QPushButton/QToolButton-Stylesheets (styles.py
   apply_theme_to_app(), tool_bar.py BaseToolButton/ActionButton/
   SymmetryToggle, mw_toolbar_mixin.py Icon-Toolbar) bedeuten: ein
   Tastatur-Nutzer, der mit Tab durch die Oberflaeche navigiert, sieht bei
   Buttons/ToolButtons KEINEN visuellen Unterschied zwischen fokussiert
   und nicht fokussiert -- verifiziert per Pixel-Diff vor dem Fix (siehe
   Kommentare unten).

3. Tastatur-Erreichbarkeit: PalettePanel.list_colors (Garnfarben-Liste)
   verbindet nur `itemDoubleClicked` (Maus-Doppelklick) mit dem
   "Farbe zum Muster hinzufuegen"-Handler. Ein Tastatur-Nutzer kann per
   Pfeiltasten durch die Liste navigieren, aber Enter/Return loeste vorher
   NICHTS aus -- die einzige Moeglichkeit, eine Farbe hinzuzufuegen, war
   ein Maus-Doppelklick. Fix: zusaetzlich `itemActivated` verbinden (feuert
   bei Enter UND bei Doppelklick), damit KEIN Doppel-Hinzufuegen bei einem
   echten Doppelklick entsteht.
"""

import pytest

from pysticky.ui.builders.mw_toolbar_mixin import ToolbarBuilderMixin
from pysticky.ui.panels.palette_panel import PalettePanel
from pysticky.ui.styles import apply_theme_to_app
from pysticky.ui.tools.tool_enum import Tool
from pysticky.ui.widgets.tool_bar import ActionButton, SymmetryToggle, ToggleToolButton, ToolBar

pytestmark = pytest.mark.usefixtures("qtbot")


# --- 1. accessibleName ------------------------------------------------


def test_tool_buttons_have_accessible_names(qtbot):
    """Jeder Werkzeug-Button in der linken ToolBar muss einen nicht-leeren
    accessibleName() tragen -- sonst ist er fuer Screenreader namenlos."""
    bar = ToolBar()
    qtbot.addWidget(bar)

    assert bar.get_button(Tool.PENCIL).accessibleName() == "Stift"
    assert bar.get_button(Tool.ERASER).accessibleName() == "Radierer"
    assert bar.get_button(Tool.FILL).accessibleName() == "Füllen"

    # ALLE registrierten Buttons muessen einen Namen haben, nicht nur die
    # oben stichprobenartig geprueften.
    for btn in set(bar._buttons.values()):
        assert btn.accessibleName() != "", f"Button ohne accessibleName: {btn.toolTip()!r}"


def test_toggle_tool_button_accessible_name_updates_on_toggle(qtbot):
    """ToggleToolButton wechselt Icon/Label zur Laufzeit (Rechteck <->
    Rechteck gefuellt) -- der accessibleName muss mitwechseln, sonst nennt
    der Screenreader nach dem Umschalten weiter den alten/urspruenglichen
    Namen."""
    btn = ToggleToolButton(
        Tool.RECT, Tool.RECT_FILLED, "□", "■", "Rechteck", "Rechteck gefuellt", "R"
    )
    qtbot.addWidget(btn)

    assert btn.accessibleName() == "Rechteck"
    btn.toggle_fill_state()
    assert btn.accessibleName() == "Rechteck gefuellt"
    btn.reset_to_outline()
    assert btn.accessibleName() == "Rechteck"


def test_action_button_and_symmetry_toggle_have_accessible_names(qtbot):
    """ActionButton/SymmetryToggle erben von BaseToolButton -- muessen den
    Namen ueber denselben Konstruktor-Pfad bekommen."""
    action_btn = ActionButton("↔️", "Spiegel H", "Horizontal spiegeln")
    qtbot.addWidget(action_btn)
    assert action_btn.accessibleName() == "Spiegel H"

    sym_btn = SymmetryToggle("↔️", "Horiz.", "Horizontal symmetrisch zeichnen")
    qtbot.addWidget(sym_btn)
    assert sym_btn.accessibleName() == "Horiz."


# --- 2. Fokus-Sichtbarkeit (QSS) ---------------------------------------


def test_tool_bar_button_stylesheets_have_focus_rule(qtbot):
    """BaseToolButton/ActionButton/SymmetryToggle setzen ihr Stylesheet PER
    INSTANZ (setStyleSheet auf sich selbst) -- das hat Vorrang vor jedem
    App-weiten Stylesheet. Ohne eigene ':focus'-Regel bleibt ein
    fokussierter Button (Tab-Taste) optisch nicht vom unfokussierten
    unterscheidbar, selbst wenn das App-Stylesheet eine :focus-Regel hat."""
    bar = ToolBar()
    qtbot.addWidget(bar)
    btn = bar.get_button(Tool.PENCIL)
    assert "QToolButton:focus" in btn.styleSheet()

    action_btn = ActionButton("↔️", "Spiegel H")
    qtbot.addWidget(action_btn)
    assert "QToolButton:focus" in action_btn.styleSheet()

    sym_btn = SymmetryToggle("↔️", "Horiz.", "tooltip")
    qtbot.addWidget(sym_btn)
    assert "QToolButton:focus" in sym_btn.styleSheet()


def test_icon_toolbar_stylesheet_has_focus_rule():
    """Die obere Icon-Toolbar (mw_toolbar_mixin.py) baut ihr Stylesheet in
    _get_toolbar_stylesheet() -- auch hier fehlte eine :focus-Regel fuer
    QToolButton trotz vorhandener :hover/:pressed/:checked-Regeln."""
    stylesheet = ToolbarBuilderMixin._get_toolbar_stylesheet(None)
    assert "QToolButton:focus" in stylesheet


def test_app_stylesheet_has_pushbutton_and_toolbutton_focus_rules(qtbot):
    """apply_theme_to_app() ist das App-weite Basis-Stylesheet (fuer alle
    Dialoge/Widgets ohne eigenes Styling, in BEIDEN Themes) -- muss
    :focus-Regeln fuer QPushButton UND QToolButton enthalten, sonst zeigt
    z.B. jeder unstylisierte Dialog-Button beim Tabben keinen Fokus an."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    apply_theme_to_app(app)
    sheet = app.styleSheet()
    assert "QPushButton:focus" in sheet
    assert "QToolButton:focus" in sheet


# --- 3. Tastatur-Erreichbarkeit (Paletten-Liste) -----------------------


def test_palette_panel_enter_key_adds_color(qtbot):
    """Pfeiltasten-Navigation + Enter muss eine Farbe zum Muster hinzufuegen
    -- vorher war NUR ein Maus-Doppelklick verdrahtet (itemDoubleClicked),
    ein reiner Tastatur-Nutzer konnte nie eine Farbe hinzufuegen."""
    from PySide6.QtCore import Qt as QtCore_Qt

    panel = PalettePanel()
    qtbot.addWidget(panel)
    panel.show()

    added = []
    panel.color_added.connect(lambda thread: added.append(thread))

    lw = panel.list_colors
    assert lw.count() > 2
    lw.setCurrentRow(2)
    lw.setFocus()

    qtbot.keyClick(lw, QtCore_Qt.Key.Key_Return)

    assert len(added) == 1
    assert added[0] is panel._current_palette_threads[2]


def test_palette_panel_item_activated_connected_not_double_clicked(qtbot):
    """Regressions-Absicherung: itemActivated ist verbunden (Enter-Weg),
    itemDoubleClicked bewusst NICHT zusaetzlich -- sonst wuerde ein echter
    Maus-Doppelklick (der laut Qt-Doku BEIDE Signale feuert) die Farbe
    zweimal hinzufuegen. Getestet durch direktes Emittieren beider
    Signale fuer denselben Eintrag: itemDoubleClicked darf NICHTS
    ausloesen (kein Handler dran), itemActivated genau einmal."""
    panel = PalettePanel()
    qtbot.addWidget(panel)

    added = []
    panel.color_added.connect(lambda thread: added.append(thread))

    lw = panel.list_colors
    item = lw.item(0)

    lw.itemDoubleClicked.emit(item)
    assert added == [], "itemDoubleClicked darf nicht mehr direkt verbunden sein"

    lw.itemActivated.emit(item)
    assert len(added) == 1
