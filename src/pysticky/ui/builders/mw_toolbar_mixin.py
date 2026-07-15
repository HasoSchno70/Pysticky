"""
Toolbar-Builder-Mixin für MainWindow.

Enthält die Erstellung der Toolbar und Hilfsmethoden.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QComboBox, QFrame, QLabel, QToolButton, QWidget

from ...core.i18n import t
from ..styles import THEME
from ..widgets.icon_toolbar import IconToolBar

if TYPE_CHECKING:
    from ..main_window import MainWindow


class ToolbarBuilderMixin:
    """Mixin für Toolbar-Erstellung."""

    def _create_toolbar(self: "MainWindow") -> None:
        """Erstellt die Toolbar mit Icons und farblich gruppierten Sektionen.

        Eigenes ``IconToolBar``-Widget statt nativer ``QToolBar`` — dadurch
        scrollt die Leiste bei schmalen Fenstern per Hover genauso wie die
        linke Werkzeugleiste, statt Qt's ">>"-Ueberlaufmenue zu zeigen.
        Eingehaengt wird sie in ``_create_central_widget`` (MainWindow).
        """
        self._emoji_actions: list[tuple[QAction, str, int]] = []
        self._emoji_buttons: list[tuple[QToolButton, str, int]] = []
        self._toolbar_section_buttons: list[tuple[QToolButton, str]] = []

        toolbar = IconToolBar()
        self._toolbar = toolbar

        # === DATEI === (gruen)
        self._add_toolbar_action(toolbar, self.action_new, "📄", t("Neu"), section="file")
        self._add_toolbar_action(toolbar, self.action_open, "📂", t("Öffnen"), section="file")
        self._add_toolbar_action(toolbar, self.action_save, "💾", t("Speichern"), section="file")
        self._add_section_divider(toolbar, THEME.accent_primary)

        # === BEARBEITEN === (orange)
        self._add_toolbar_action(toolbar, self.action_undo, "↩️", t("Rückgängig"), section="edit")
        self._add_toolbar_action(toolbar, self.action_redo, "↪️", t("Wiederholen"), section="edit")
        self._add_section_divider(toolbar, THEME.accent_secondary)

        # === ZOOM === (blau)
        self._add_toolbar_action(
            toolbar, self.action_zoom_in, "🔍", t("Vergrößern"), section="zoom"
        )
        self._add_toolbar_action(
            toolbar, self.action_zoom_out, "🔎", t("Verkleinern"), section="zoom"
        )
        self._add_toolbar_action(
            toolbar, self.action_zoom_fit, "⬜", t("Einpassen"), section="zoom"
        )
        self._add_section_divider(toolbar, THEME.info)

        # === MODUS === (Cyan/Akzent) — prominenter Stitch/Diamond-Switch
        self._add_mode_switch(toolbar)
        self._add_section_divider(toolbar, THEME.accent_purple)

        # === ANSICHT === (lila)
        self._add_view_toggles(toolbar)
        self._add_section_divider(toolbar, THEME.accent_purple)

        # === SYMMETRIE === (pink-ish error)
        self._add_symmetry_controls(toolbar)
        self._add_section_divider(toolbar, THEME.error)

        # === STICH/SNAP === (warning gelb)
        self.chk_snap_grid = self._create_toggle_button(
            "🧲", t("Snap"), t("Magnetisches Raster"), section="stitch"
        )
        self.chk_snap_grid.toggled.connect(self._on_snap_grid_changed)
        toolbar.addWidget(self.chk_snap_grid)
        self._add_stitch_type_picker(toolbar)
        self._add_section_divider(toolbar, THEME.warning)

        # === EINSTELLUNGEN ===
        # Garn-Vorrat bekommt einen eigenen Toolbar-Button — vorher nur tief
        # im Bearbeiten-Menue versteckt (schwer zu finden, siehe User-Feedback).
        self._add_toolbar_action(
            toolbar, self.action_inventory, "🧶", t("Garn-Vorrat"), section="misc"
        )
        self._add_toolbar_action(
            toolbar, self.action_settings, "⚙️", t("Einstellungen"), section="misc"
        )

        toolbar.setStyleSheet(self._get_toolbar_stylesheet())
        toolbar.reapply_hint_style(THEME.accent_primary, THEME.bg_dark)
        toolbar.finalize()

    def _add_section_divider(self, toolbar: IconToolBar, color: str) -> None:
        """Vertikale Trennlinie in der angegebenen Akzentfarbe.

        WICHTIG: Wrapper + Line werden mit ``parent=toolbar`` konstruiert.
        Sonst sind sie zwischen Konstruktor und ``toolbar.addWidget`` kurz
        Top-Level-Widgets und Qt zeigt sie beim ersten Show-Event als
        14×15-Phantomfenster im Tab-Bar-Bereich. Das war besonders beim
        DP→Stick-Wechsel sichtbar, weil dort die Toolbar-Repaints durch
        die ``setUpdatesEnabled``-Rueckkehr getriggert wurden.
        """
        wrapper = QWidget(toolbar)
        wrapper.setFixedWidth(14)
        from PySide6.QtWidgets import QHBoxLayout

        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)
        line = QFrame(wrapper)
        line.setFixedWidth(2)
        line.setStyleSheet(
            f"background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            f"stop:0 transparent, stop:0.2 {color}, "
            f"stop:0.8 {color}, stop:1 transparent); "
            f"border-radius: 1px;"
        )
        layout.addWidget(line)
        toolbar.addWidget(wrapper)

    def _add_stitch_type_picker(self: "MainWindow", toolbar: IconToolBar) -> None:
        """Fuegt einen kompakten Stichtyp-Picker (QComboBox mit Glyphen) hinzu."""
        # parent=toolbar verhindert Top-Level-Phantom beim ersten Show.
        self.combo_stitch_type_label = QLabel(t("Stich:"), toolbar)
        self.combo_stitch_type_label.setStyleSheet(
            f"color: {THEME.text_muted}; padding: 0 4px 0 8px;"
        )
        toolbar.addWidget(self.combo_stitch_type_label)

        self.combo_stitch_type = QComboBox()
        self.combo_stitch_type.setToolTip(
            t(
                "Stichtyp fuer neue Stiche.\n"
                "Voll, halb (/), halb (\\), oder einer von vier Viertelstichen."
            )
        )
        for stype, glyph, text_label, _shortcut in self.STITCH_TYPE_ENTRIES:
            # Glyph + verkuerzter Label-Teil, damit Combobox kompakt bleibt
            translated = t(text_label)
            short = (
                translated.split("(")[0]
                .strip()
                .replace("Kreuzstich", "")
                .replace("cross stitch", "")
                .strip()
                or translated
            )
            self.combo_stitch_type.addItem(f"{glyph}  {short}", userData=stype)
        self.combo_stitch_type.setCurrentIndex(0)
        self.combo_stitch_type.currentIndexChanged.connect(self._on_stitch_type_picker_changed)
        toolbar.addWidget(self.combo_stitch_type)

    def _on_stitch_type_picker_changed(self: "MainWindow", index: int) -> None:
        """Toolbar-Dropdown geaendert -> normalen Handler triggern."""
        stype = self.combo_stitch_type.itemData(index)
        if stype is None:
            return
        self._on_stitch_type_changed(int(stype))

    def _get_toolbar_stylesheet(self) -> str:
        """Gibt das Stylesheet für die Toolbar zurück (mit Section-Tints)."""
        from ..styles import THEME

        def tint(hex_color: str, alpha: int) -> str:
            c = QColor(hex_color)
            return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha})"

        # Default-Look (transparent) + Tints je section. Tints sind dezent —
        # man sieht die Gruppe als sanfter Hintergrund, der Button selbst
        # bleibt klar erkennbar.
        return f"""
            IconToolBar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {THEME.bg_light}, stop:0.5 {THEME.bg_medium}, stop:1 {THEME.bg_light});
                border-bottom: 2px solid {THEME.accent_primary};
            }}
            QToolButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 4px 6px;
                color: {THEME.text_secondary};
                font-size: 10px;
                font-weight: 600;
            }}
            QToolButton[section="file"]      {{ background: {tint(THEME.accent_primary, 30)}; }}
            QToolButton[section="edit"]      {{ background: {tint(THEME.accent_secondary, 30)}; }}
            QToolButton[section="zoom"]      {{ background: {tint(THEME.info, 30)}; }}
            QToolButton[section="view"]      {{ background: {tint(THEME.accent_purple, 30)}; }}
            QToolButton[section="symmetry"]  {{ background: {tint(THEME.error, 30)}; }}
            QToolButton[section="stitch"]    {{ background: {tint(THEME.warning, 30)}; }}

            QToolButton:hover                {{ background: {tint(THEME.accent_primary, 70)}; color: {THEME.text_primary}; border-color: {THEME.accent_primary}; }}
            QToolButton[section="edit"]:hover     {{ background: {tint(THEME.accent_secondary, 70)}; border-color: {THEME.accent_secondary}; }}
            QToolButton[section="zoom"]:hover     {{ background: {tint(THEME.info, 70)}; border-color: {THEME.info}; }}
            QToolButton[section="view"]:hover     {{ background: {tint(THEME.accent_purple, 70)}; border-color: {THEME.accent_purple}; }}
            QToolButton[section="symmetry"]:hover {{ background: {tint(THEME.error, 70)}; border-color: {THEME.error}; }}
            QToolButton[section="stitch"]:hover   {{ background: {tint(THEME.warning, 90)}; border-color: {THEME.warning}; }}

            QToolButton:pressed              {{ background: {THEME.accent_primary}; color: {THEME.bg_dark}; }}
            QToolButton:checked              {{
                background: {tint(THEME.accent_primary, 120)};
                border: 2px solid {THEME.accent_primary};
                color: {THEME.text_primary};
                padding: 3px 5px;  /* kompensiert dickere Border */
            }}
            QToolButton[section="view"]:checked     {{ background: {tint(THEME.accent_purple, 120)}; border-color: {THEME.accent_purple}; }}
            QToolButton[section="symmetry"]:checked {{ background: {tint(THEME.error, 120)}; border-color: {THEME.error}; }}
            QToolButton[section="stitch"]:checked   {{ background: {tint(THEME.warning, 140)}; border-color: {THEME.warning}; }}
            QToolButton:disabled             {{ color: {THEME.text_disabled}; background: transparent; }}

            /* Modus-Umschalter: bewusst auffaelliger als die uebrigen
               Toggle-Buttons — zeigt den AKTUELLEN Modus, nicht das Ziel,
               und hebt sich per Farbe/Groesse klar vom Rest der Toolbar ab. */
            QToolButton#modeSwitchBtn {{
                font-size: 13px;
                font-weight: 800;
                padding: 6px 16px;
                border-radius: 8px;
                border: 2px solid transparent;
            }}
            QToolButton#modeSwitchBtn[stitchMode="true"] {{
                background: {tint(THEME.accent_secondary, 130)};
                border-color: {THEME.accent_secondary};
                color: {THEME.text_primary};
            }}
            QToolButton#modeSwitchBtn[stitchMode="true"]:hover {{
                background: {tint(THEME.accent_secondary, 190)};
            }}
            QToolButton#modeSwitchBtn[stitchMode="false"] {{
                background: {tint(THEME.accent_purple, 130)};
                border-color: {THEME.accent_purple};
                color: {THEME.text_primary};
            }}
            QToolButton#modeSwitchBtn[stitchMode="false"]:hover {{
                background: {tint(THEME.accent_purple, 190)};
            }}
        """

    def _add_mode_switch(self: "MainWindow", toolbar: IconToolBar) -> None:
        """Fuegt den Stitch/Diamond-Mode-Switch in die Toolbar ein.

        Zeigt IMMER den AKTUELLEN Modus (nicht das Wechselziel) — Text,
        Icon und Hintergrundfarbe machen auf einen Blick klar, in welchem
        Modus man gerade arbeitet. Eigene, kraeftigere Styling-Klasse
        (#modeSwitchBtn, siehe _get_toolbar_stylesheet) statt der
        generischen Toggle-Button-Tints, damit sich der Schalter deutlich
        vom Rest der Toolbar abhebt.

        QLabel mit parent=toolbar erzeugen, sonst kurzes Top-Level-Phantom
        beim ersten Show / nach setUpdatesEnabled-Refresh.
        """
        label = QLabel(t("Modus:"), toolbar)
        label.setStyleSheet(f"color: {THEME.text_primary}; font-weight: 700; padding: 0 4px 0 8px;")
        toolbar.addWidget(label)

        self.btn_mode_switch = self._create_toggle_button(
            "🧵",
            t("Kreuzstich"),
            t(
                "Aktueller Modus: Kreuzstich.\n"
                "Klicken, um zu Diamond-Painting zu wechseln "
                "(laedt automatisch die DMC-Diamond-Painting-Palette)."
            ),
            section="mode",
        )
        self.btn_mode_switch.setObjectName("modeSwitchBtn")
        self.btn_mode_switch.setProperty("stitchMode", "true")
        self.btn_mode_switch.setMinimumWidth(130)
        self.btn_mode_switch.toggled.connect(self._on_mode_switch_toggled)
        toolbar.addWidget(self.btn_mode_switch)

    def _refresh_mode_switch_button(self: "MainWindow") -> None:
        """Aktualisiert Icon/Text/Tooltip/Farbe des Mode-Buttons nach Modus-Wechsel."""
        btn = getattr(self, "btn_mode_switch", None)
        if btn is None:
            return
        is_diamond = btn.isChecked()
        if is_diamond:
            emoji = "💎"
            btn.setText(t("Diamond"))
            btn.setToolTip(
                t("Aktueller Modus: Diamond-Painting.\nKlicken, um zu Kreuzstich zu wechseln.")
            )
        else:
            emoji = "🧵"
            btn.setText(t("Kreuzstich"))
            btn.setToolTip(
                t(
                    "Aktueller Modus: Kreuzstich.\n"
                    "Klicken, um zu Diamond-Painting zu wechseln "
                    "(laedt automatisch die DMC-Diamond-Painting-Palette)."
                )
            )
        # Dynamic-Property fuer die #modeSwitchBtn-QSS-Selektoren — Qt
        # wertet Property-Selektoren nur nach explizitem Re-Polish neu aus.
        btn.setProperty("stitchMode", "false" if is_diamond else "true")
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        # Icon neu erzeugen und im Emoji-Cache-Tupel updaten (sonst wird
        # beim Theme-Wechsel weiterhin das alte Emoji gerendert).
        btn.setIcon(QIcon(self._create_emoji_icon(emoji, 20)))
        for i, (b, _, size) in enumerate(self._emoji_buttons):
            if b is btn:
                self._emoji_buttons[i] = (btn, emoji, size)
                break

    def _on_mode_switch_toggled(self: "MainWindow", checked: bool) -> None:
        """Toolbar-Button wurde geklickt — Diamond-View an/aus, Button-Look syncen."""
        self._on_toggle_diamond_view(checked)
        self._refresh_mode_switch_button()

    def _add_view_toggles(self: "MainWindow", toolbar: IconToolBar) -> None:
        """Fügt Ansicht-Toggle-Buttons hinzu."""
        self.chk_symbols = self._create_toggle_button(
            "🔠", t("Symbole"), t("Symbole anzeigen"), section="view"
        )
        self.chk_symbols.toggled.connect(self._on_toggle_symbols)
        toolbar.addWidget(self.chk_symbols)

        self.chk_backstitches = self._create_toggle_button(
            "↙️", t("Rückstiche"), t("Rückstiche anzeigen"), section="view"
        )
        self.chk_backstitches.toggled.connect(self._on_toggle_backstitches)
        toolbar.addWidget(self.chk_backstitches)

        self.chk_only_active = self._create_toggle_button(
            "🗗", t("Nur Ebene"), t("Nur aktive Ebene anzeigen"), section="view"
        )
        self.chk_only_active.toggled.connect(self._on_toggle_only_active)
        toolbar.addWidget(self.chk_only_active)

    def _add_symmetry_controls(self: "MainWindow", toolbar: IconToolBar) -> None:
        """Fügt Symmetrie-Steuerelemente hinzu."""
        sym_label = QLabel(" 🔀 ", toolbar)  # parent verhindert Phantom-Top-Level
        sym_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 14px;")
        sym_label.setToolTip(t("Symmetrie-Einstellungen"))
        toolbar.addWidget(sym_label)

        self.chk_symmetry_h = self._create_toggle_button(
            "↔️", t("Horiz."), t("Horizontal symmetrisch zeichnen"), section="symmetry"
        )
        self.chk_symmetry_h.toggled.connect(self._on_symmetry_h_changed)
        toolbar.addWidget(self.chk_symmetry_h)

        self.chk_symmetry_v = self._create_toggle_button(
            "↕️", t("Vert."), t("Vertikal symmetrisch zeichnen"), section="symmetry"
        )
        self.chk_symmetry_v.toggled.connect(self._on_symmetry_v_changed)
        toolbar.addWidget(self.chk_symmetry_v)

        # Symmetrie-Modus Dropdown
        self.combo_symmetry = QComboBox()
        self.combo_symmetry.addItems([t("Aus"), "2x ↔", "2x ↕", t("4-fach"), t("8-fach")])
        self.combo_symmetry.setToolTip(t("Symmetrie-Modus wählen"))
        self.combo_symmetry.setMinimumWidth(80)
        self.combo_symmetry.setStyleSheet(self._get_combobox_stylesheet())
        self.combo_symmetry.currentIndexChanged.connect(self._on_symmetry_mode_changed)
        toolbar.addWidget(self.combo_symmetry)

        self.chk_center_cross = self._create_toggle_button(
            "✞", t("Mitte"), t("Zentrierhilfe anzeigen"), section="symmetry"
        )
        self.chk_center_cross.toggled.connect(self._on_center_crosshair_changed)
        toolbar.addWidget(self.chk_center_cross)

    def _get_combobox_stylesheet(self) -> str:
        """Gibt das Stylesheet für ComboBoxen zurück."""
        from ..styles import THEME

        return f"""
            QComboBox {{
                background: {THEME.bg_dark};
                border: 1px solid {THEME.border_light};
                border-radius: 4px;
                padding: 4px 8px;
                color: {THEME.text_secondary};
                font-size: 11px;
            }}
            QComboBox:hover {{ border-color: {THEME.accent_primary}; }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 8px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {THEME.text_muted};
            }}
            QComboBox QAbstractItemView {{
                background: {THEME.bg_dark};
                border: 1px solid {THEME.border_light};
                color: {THEME.text_secondary};
                selection-background-color: {THEME.accent_primary};
            }}
        """

    def _add_toolbar_action(
        self,
        toolbar: IconToolBar,
        action: QAction,
        icon_text: str,
        label: str,
        section: str = "misc",
    ) -> QToolButton:
        """Fügt eine Action mit Emoji-Icon zur Toolbar hinzu (mit Section-Tint)."""
        btn = QToolButton()
        btn.setDefaultAction(action)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        btn.setProperty("section", section)
        pixmap = self._create_emoji_icon(icon_text, 24)
        action.setIcon(QIcon(pixmap))
        action.setIconText(label)
        toolbar.addWidget(btn)
        self._emoji_actions.append((action, icon_text, 24))
        self._toolbar_section_buttons.append((btn, section))
        return btn

    def _create_toggle_button(
        self, icon_text: str, label: str, tooltip: str, section: str = "misc"
    ) -> QToolButton:
        """Erstellt einen Toggle-Button mit Emoji-Icon (mit Section-Tint)."""
        btn = QToolButton()
        btn.setCheckable(True)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        btn.setToolTip(tooltip)
        btn.setProperty("section", section)
        pixmap = self._create_emoji_icon(icon_text, 20)
        btn.setIcon(QIcon(pixmap))
        btn.setText(label)
        btn.setMinimumWidth(60)
        self._emoji_buttons.append((btn, icon_text, 20))
        self._toolbar_section_buttons.append((btn, section))
        return btn

    def _refresh_toolbar_icons(self) -> None:
        """Regeneriert alle Emoji-Icons mit aktueller Theme-Farbe."""
        for action, emoji, size in self._emoji_actions:
            action.setIcon(QIcon(self._create_emoji_icon(emoji, size)))
        for btn, emoji, size in self._emoji_buttons:
            btn.setIcon(QIcon(self._create_emoji_icon(emoji, size)))

    def _create_emoji_icon(self, emoji: str, size: int) -> QPixmap:
        """Erstellt ein Pixmap aus einem Emoji."""
        from ..styles import THEME

        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont("Segoe UI Emoji", int(size * 0.7))
        painter.setFont(font)
        painter.setPen(QColor(THEME.text_primary))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, emoji)
        painter.end()
        return pixmap
