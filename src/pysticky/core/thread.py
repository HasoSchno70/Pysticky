"""
Garn-Klassen für die Farbverwaltung.

Dieses Modul enthält die Kernklassen für die Darstellung von
Stickgarnen und deren Farben.
"""

from dataclasses import dataclass

from .color_math import lab_to_rgb, rgb_to_lab


def _blend_colors_lab(
    colors: list["ThreadColor"],
    weights: list[int],
) -> "ThreadColor":
    """
    Perzeptueller Farbmix in CIE-Lab.

    sRGB-Pixel werden zu Lab konvertiert, gewichtetes Mittel im Lab-Raum
    berechnet, dann zurück zu sRGB. So entspricht der Mix dem, was das
    Auge erwartet — anders als ein plain RGB-Mittel.

    Implementation: Inline, ohne numpy-Abhängigkeit (Thread-Klasse ist
    "core lite"). Bei <= 4 Komponenten ist Python schnell genug.
    """
    if not colors:
        raise ValueError("Mindestens eine Farbe nötig")
    if len(weights) != len(colors):
        raise ValueError("colors und weights müssen gleich lang sein")

    total_weight = sum(weights)
    if total_weight <= 0:
        raise ValueError("Summe der Weights muss > 0 sein")

    # Lab-Werte aufsummieren
    L_sum = a_sum = b_sum = 0.0
    for col, w in zip(colors, weights):
        L, a, b = rgb_to_lab(col.r, col.g, col.b)
        L_sum += L * w
        a_sum += a * w
        b_sum += b * w

    L_mix = L_sum / total_weight
    a_mix = a_sum / total_weight
    b_mix = b_sum / total_weight

    r, g, b = lab_to_rgb(L_mix, a_mix, b_mix)
    return ThreadColor(r, g, b)


@dataclass(frozen=True)
class ThreadColor:
    """
    Repräsentiert eine RGB-Farbe.

    Immutable dataclass für thread-sichere Farbdarstellung.
    Werte werden automatisch auf den gültigen Bereich 0-255 begrenzt.

    Attributes:
        r: Rot-Wert (0-255)
        g: Grün-Wert (0-255)
        b: Blau-Wert (0-255)

    Example:
        >>> color = ThreadColor(255, 128, 0)
        >>> color.to_hex()
        '#FF8000'
        >>> color.luminance
        0.6196...
    """

    r: int
    g: int
    b: int

    def __post_init__(self) -> None:
        """Validiert und begrenzt die Farbwerte auf 0-255."""
        # frozen=True erlaubt keine direkte Zuweisung,
        # daher nutzen wir object.__setattr__
        object.__setattr__(self, "r", max(0, min(255, self.r)))
        object.__setattr__(self, "g", max(0, min(255, self.g)))
        object.__setattr__(self, "b", max(0, min(255, self.b)))

    @classmethod
    def from_hex(cls, hex_color: str) -> "ThreadColor":
        """
        Erstellt eine Farbe aus einem Hex-String.

        Args:
            hex_color: Hex-Farbcode mit oder ohne '#' (z.B. "#FF0000" oder "FF0000")

        Returns:
            Neue ThreadColor-Instanz

        Raises:
            ValueError: Bei ungültigem Hex-Format

        Example:
            >>> ThreadColor.from_hex("#FF0000")
            ThreadColor(r=255, g=0, b=0)
        """
        hex_color = hex_color.lstrip("#")
        return cls(r=int(hex_color[0:2], 16), g=int(hex_color[2:4], 16), b=int(hex_color[4:6], 16))

    def to_hex(self) -> str:
        """
        Konvertiert die Farbe zu einem Hex-String.

        Returns:
            Hex-Farbcode im Format "#RRGGBB"

        Example:
            >>> ThreadColor(255, 128, 0).to_hex()
            '#FF8000'
        """
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"

    def to_tuple(self) -> tuple[int, int, int]:
        """
        Gibt die Farbe als RGB-Tuple zurück.

        Returns:
            Tuple (r, g, b) mit Werten 0-255

        Example:
            >>> ThreadColor(255, 128, 0).to_tuple()
            (255, 128, 0)
        """
        return (self.r, self.g, self.b)

    @property
    def luminance(self) -> float:
        """
        Berechnet die relative Helligkeit (Luminanz) der Farbe.

        Verwendet die ITU-R BT.601 Gewichtung für die menschliche
        Wahrnehmung von Helligkeit.

        Returns:
            Luminanz-Wert zwischen 0.0 (schwarz) und 1.0 (weiß)

        Example:
            >>> ThreadColor(255, 255, 255).luminance
            1.0
            >>> ThreadColor(0, 0, 0).luminance
            0.0
        """
        return (0.299 * self.r + 0.587 * self.g + 0.114 * self.b) / 255.0

    @property
    def is_light(self) -> bool:
        """
        Prüft ob die Farbe als hell wahrgenommen wird.

        Nützlich für die Auswahl einer kontrastierenden Textfarbe.

        Returns:
            True wenn luminance > 0.5, sonst False

        Example:
            >>> ThreadColor(255, 255, 255).is_light
            True
            >>> ThreadColor(0, 0, 0).is_light
            False
        """
        return self.luminance > 0.5


@dataclass
class Thread:
    """
    Repräsentiert ein Stickgarn mit Farbe und Metadaten.

    Attributes:
        name: Anzeigename des Garns (z.B. "Weihnachtsrot")
        color: RGB-Farbe des Garns
        manufacturer: Hersteller (z.B. "DMC", "Anchor")
        catalog_number: Katalognummer des Herstellers (z.B. "321")
        weight: Garnstärke in wt (Standard: 40)
        blend_components: Wenn gesetzt, ist dieser Thread ein "Tweed"-Blend
                          aus mehreren Komponenten-Threads (z.B. 1 Strang DMC 310
                          + 1 Strang DMC 745). `color` wird dann aus den
                          Komponenten als perzeptueller Mix (CIE-Lab) berechnet.
        strand_ratios:    Parallel zu `blend_components` — Stranganzahl pro
                          Komponente (Default 1 pro Komponente).

    Example:
        >>> thread = Thread.from_hex("Rot", "#FF0000", manufacturer="DMC", catalog_number="321")
        >>> thread.color.to_hex()
        '#FF0000'
        >>> blend = Thread.blend([dmc310, dmc745], [1, 1])
        >>> blend.color  # gemischte Farbe in Lab-Raum
    """

    name: str
    color: ThreadColor
    manufacturer: str | None = None
    catalog_number: str | None = None
    weight: int | None = 40  # Standard: 40 wt
    blend_components: list["Thread"] | None = None
    strand_ratios: list[int] | None = None

    @property
    def is_blend(self) -> bool:
        """True wenn dieser Thread ein Blend aus mehreren Komponenten ist."""
        return self.blend_components is not None and len(self.blend_components) >= 2

    @classmethod
    def blend(
        cls,
        components: list["Thread"],
        ratios: list[int] | None = None,
        name: str | None = None,
    ) -> "Thread":
        """
        Erstellt einen Tweed-Blend aus mehreren Komponenten-Threads.

        Mischfarbe wird perzeptuell in CIE-Lab berechnet (gewichtet nach
        Strang-Verhältnissen). Plain RGB-Mix wäre wahrnehmungsmäßig
        falsch — Lab-Mix erzeugt das, was der Stickerin am ehesten
        entspricht.

        Args:
            components: Liste der Komponenten-Threads (mind. 2).
            ratios:     Stranganzahl pro Komponente. Default: 1 pro Komponente.
                        Bei [1, 2] kommt z.B. 1 Strang vom ersten Thread und
                        2 Stränge vom zweiten in jede Nadel.
            name:       Anzeigename. Default: "MfrA Nr / MfrB Nr (1+1)".

        Returns:
            Neuer Thread mit `blend_components` gesetzt.
        """
        if len(components) < 2:
            raise ValueError("Blend braucht mindestens 2 Komponenten")
        if ratios is None:
            ratios = [1] * len(components)
        if len(ratios) != len(components):
            raise ValueError("Anzahl Ratios muss Anzahl Komponenten entsprechen")
        if any(r < 1 for r in ratios):
            raise ValueError("Ratios müssen >= 1 sein")

        mixed_color = _blend_colors_lab([c.color for c in components], ratios)

        if name is None:
            parts = [
                f"{c.manufacturer or ''} {c.catalog_number or c.name}".strip() for c in components
            ]
            ratio_str = "+".join(str(r) for r in ratios)
            name = f"{' / '.join(parts)} ({ratio_str})"

        # Manufacturer/Catalog: bei homogenem Blend (alle DMC) bleibt das,
        # sonst leer.
        mfrs = {c.manufacturer for c in components if c.manufacturer}
        manufacturer = mfrs.pop() if len(mfrs) == 1 else "Blend"
        catalog = "+".join(c.catalog_number or "" for c in components)

        return cls(
            name=name,
            color=mixed_color,
            manufacturer=manufacturer,
            catalog_number=catalog,
            blend_components=list(components),
            strand_ratios=list(ratios),
        )

    @classmethod
    def from_hex(cls, name: str, hex_color: str, **kwargs) -> "Thread":
        """
        Erstellt ein Garn mit einer Hex-Farbe.

        Convenience-Methode für die schnelle Erstellung eines Garns
        ohne separate ThreadColor-Instanziierung.

        Args:
            name: Name des Garns
            hex_color: Hex-Farbcode (z.B. "#FF0000")
            **kwargs: Weitere Attribute (manufacturer, catalog_number, weight)

        Returns:
            Neue Thread-Instanz

        Example:
            >>> Thread.from_hex("Rot", "#FF0000", manufacturer="DMC")
            Thread('Rot', #FF0000)
        """
        return cls(name=name, color=ThreadColor.from_hex(hex_color), **kwargs)

    def __repr__(self) -> str:
        """Gibt eine lesbare String-Repräsentation zurück."""
        return f"Thread('{self.name}', {self.color.to_hex()})"


# Vordefinierte Standard-Farben (ähnlich wie bei Stickmaschinen)
DEFAULT_THREAD_COLORS: list[Thread] = [
    Thread.from_hex("Schwarz", "#000000"),
    Thread.from_hex("Weiß", "#FFFFFF"),
    Thread.from_hex("Rot", "#FF0000"),
    Thread.from_hex("Grün", "#00FF00"),
    Thread.from_hex("Blau", "#0000FF"),
    Thread.from_hex("Gelb", "#FFFF00"),
    Thread.from_hex("Orange", "#FF8000"),
    Thread.from_hex("Rosa", "#FF80C0"),
    Thread.from_hex("Violett", "#8000FF"),
    Thread.from_hex("Braun", "#804000"),
    Thread.from_hex("Grau", "#808080"),
    Thread.from_hex("Türkis", "#00C0C0"),
    Thread.from_hex("Gold", "#FFD700"),
    Thread.from_hex("Silber", "#C0C0C0"),
    Thread.from_hex("Bordeaux", "#800020"),
    Thread.from_hex("Marineblau", "#000080"),
]
"""Vordefinierte Standard-Garne für neue Projekte."""
