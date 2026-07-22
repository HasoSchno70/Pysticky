"""
XSD (Pattern Maker) Dateiformat-Import.

Pattern Maker XSD ist ein proprietäres Binärformat.
Diese Implementierung basiert auf Reverse-Engineering und
Community-Dokumentation des Formats.

Unterstützte Features:
- Grid-Daten (Kreuzstiche)
- Farbpalette
- Rückstiche (Backstitches)
- Grundlegende Metadaten

Nicht unterstützt:
- Komplexe Stich-Typen (French Knots, etc.)
- Eingebettete Bilder
- Erweiterte Metadaten
"""

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from ...core.layer import Layer
from ...core.pattern import ColorEntry, Pattern
from ...core.thread import Thread, ThreadColor
from ._binary import decode_string, read_exact


@dataclass
class XSDHeader:
    """XSD-Datei Header-Struktur."""

    signature: bytes
    version: int
    width: int
    height: int
    color_count: int
    has_backstitches: bool
    title: str
    author: str


class XSDImportError(Exception):
    """Fehler beim Importieren einer XSD-Datei."""

    pass


class XSDImporter:
    """
    Importiert Pattern Maker XSD-Dateien.

    Das XSD-Format ist wie folgt aufgebaut:
    - Header mit Signatur und Metadaten
    - Farbpalette
    - Grid-Daten (RLE-komprimiert oder roh)
    - Optional: Backstitch-Daten
    """

    # Bekannte XSD-Signaturen
    SIGNATURES = [
        b"PM",  # Pattern Maker
        b"PMX",  # Pattern Maker Extended
        b"\x00PM",  # Alternative Signatur
    ]

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self._invalid_color_index_warned = False

    def can_import(self, filepath: Path | str) -> bool:
        """Prüft ob die Datei ein XSD-Format ist."""
        filepath = Path(filepath)

        if not filepath.exists():
            return False

        if filepath.suffix.lower() != ".xsd":
            return False

        try:
            with open(filepath, "rb") as f:
                header = f.read(10)
                # Prüfe auf bekannte Signaturen
                for sig in self.SIGNATURES:
                    if header.startswith(sig):
                        return True
                # Manche XSD haben keine Signatur, prüfe Dateigröße
                return filepath.stat().st_size > 100
        except OSError:
            return False

    def import_file(self, filepath: Path | str) -> Pattern | None:
        """
        Importiert eine XSD-Datei.

        Args:
            filepath: Pfad zur XSD-Datei

        Returns:
            Pattern oder None bei Fehler
        """
        filepath = Path(filepath)
        self.errors.clear()
        self.warnings.clear()
        self._invalid_color_index_warned = False

        if not filepath.exists():
            self.errors.append(f"Datei nicht gefunden: {filepath}")
            return None

        try:
            with open(filepath, "rb") as f:
                return self._parse_xsd(f, filepath.stem)
        except XSDImportError as e:
            self.errors.append(str(e))
            return None
        except Exception as e:  # catch-all: format may have unexpected structure
            self.errors.append(f"Unerwarteter Fehler: {e}")
            return None

    def _parse_xsd(self, f: BinaryIO, name: str) -> Pattern:
        """Parst den XSD-Dateiinhalt."""

        # Header lesen
        header = self._read_header(f)

        if header.width < 1 or header.height < 1:
            raise XSDImportError(f"Ungültige Dimensionen: {header.width}x{header.height}")

        # Width/Height kommen aus einem ungeprüften struct.unpack ("<HH",
        # max. 65535 je Achse) -- ohne Obergrenze könnte eine beschädigte
        # Datei eine ~4,3-Milliarden-Zellen-Allokation auslösen. Gleiche
        # Grenzen wie file_io.py/pat_import.py/oxs_io.py (harte Grenze).
        if header.width > 2000 or header.height > 2000:
            raise XSDImportError(
                f"Mustergröße zu groß: {header.width}x{header.height} (max. 2000x2000)"
            )

        if header.width > 1000 or header.height > 1000:
            self.warnings.append(f"Große Muster-Dimensionen: {header.width}x{header.height}")

        # Pattern erstellen
        pattern = Pattern(name=header.title or name, width=header.width, height=header.height)
        pattern.color_entries.clear()

        # Metadaten
        if header.author:
            pattern.metadata["author"] = header.author
        pattern.metadata["imported_from"] = "xsd"
        pattern.metadata["xsd_version"] = header.version

        # Farbpalette lesen
        self._read_colors(f, pattern, header.color_count)

        # Grid-Daten lesen
        self._read_grid(f, pattern)

        # Backstitch-Daten lesen (falls vorhanden)
        if header.has_backstitches:
            self._read_backstitches(f, pattern)

        # Stichzahlen berechnen
        pattern.recalculate_stitch_counts()

        return pattern

    def _read_header(self, f: BinaryIO) -> XSDHeader:
        """Liest den XSD-Header."""

        # Signatur prüfen (3 Bytes)
        signature = f.read(3)

        # Erste 2 Bytes bestimmen das Format
        if signature[:2] == b"PM":
            return self._read_pm_header(f, signature)
        else:
            # Fallback: Versuche alternatives Format
            return self._read_generic_header(f, signature)

    def _read_pm_header(self, f: BinaryIO, signature: bytes) -> XSDHeader:
        """Liest Pattern Maker Header."""

        # Version (1 Byte)
        version = struct.unpack("B", read_exact(f, 1, "Version"))[0]

        # Dimensionen (4 Bytes: 2x uint16 LE)
        width, height = struct.unpack("<HH", read_exact(f, 4, "Dimensionen"))

        # Farbanzahl (2 Bytes)
        color_count = struct.unpack("<H", read_exact(f, 2, "Farbanzahl"))[0]

        # Flags (2 Bytes)
        flags = struct.unpack("<H", read_exact(f, 2, "Flags"))[0]
        has_backstitches = bool(flags & 0x01)

        # Titel (null-terminiert, max 64 Bytes)
        title = self._read_string(f, 64)

        # Author (null-terminiert, max 32 Bytes)
        author = self._read_string(f, 32)

        return XSDHeader(
            signature=signature,
            version=version,
            width=width,
            height=height,
            color_count=color_count,
            has_backstitches=has_backstitches,
            title=title,
            author=author,
        )

    def _read_generic_header(self, f: BinaryIO, first_bytes: bytes) -> XSDHeader:
        """Liest generischen Header für unbekannte XSD-Varianten."""

        # Versuche Dimensionen an Offset 0x10 zu lesen
        f.seek(0x10)

        try:
            width, height = struct.unpack("<HH", read_exact(f, 4, "Dimensionen"))
            color_count = struct.unpack("<H", read_exact(f, 2, "Farbanzahl"))[0]

            if width < 1 or height < 1 or width > 2000 or height > 2000:
                # Versuche anderes Offset
                f.seek(0x08)
                width, height = struct.unpack("<HH", read_exact(f, 4, "Dimensionen"))
                color_count = struct.unpack("<H", read_exact(f, 2, "Farbanzahl"))[0]

            return XSDHeader(
                signature=first_bytes,
                version=0,
                width=width,
                height=height,
                color_count=min(color_count, 256),
                has_backstitches=False,
                title="",
                author="",
            )
        except (KeyError, AttributeError, ValueError, struct.error, EOFError):
            raise XSDImportError("Kann Header nicht lesen - unbekanntes XSD-Format")

    def _read_string(self, f: BinaryIO, max_len: int) -> str:
        """Liest einen null-terminierten String."""
        return decode_string(f.read(max_len))

    def _read_colors(self, f: BinaryIO, pattern: Pattern, count: int) -> None:
        """Liest die Farbpalette."""

        # Standard-Symbole
        symbols = (
            "●○■□▲△◆◇★☆+×/\\~@&%#$!?=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        )

        for i in range(count):
            try:
                # RGB (3 Bytes)
                r, g, b = struct.unpack("BBB", f.read(3))

                # Name (null-terminiert, 32 Bytes)
                name = self._read_string(f, 32)
                if not name:
                    name = f"Farbe {i + 1}"

                # DMC-Nummer (optional, 8 Bytes)
                dmc_data = f.read(8)
                dmc_number = self._read_string_from_bytes(dmc_data)

                # Symbol (1 Byte) — Wert wird verworfen, nur Position vorschieben
                f.read(1)
                symbol = symbols[i % len(symbols)]

                thread = Thread(
                    name=name,
                    color=ThreadColor(r, g, b),
                    manufacturer="DMC" if dmc_number else "",
                    catalog_number=dmc_number,
                )

                entry = ColorEntry(thread=thread, symbol=symbol, stitch_count=0)
                pattern.color_entries.append(entry)

            except (KeyError, AttributeError, ValueError, struct.error) as e:
                self.warnings.append(f"Fehler beim Lesen von Farbe {i}: {e}")
                # Dummy-Farbe
                thread = Thread.from_hex(f"Farbe {i + 1}", "#808080")
                pattern.color_entries.append(
                    ColorEntry(thread=thread, symbol=symbols[i % len(symbols)])
                )

    def _read_string_from_bytes(self, data: bytes) -> str:
        """Extrahiert String aus Byte-Array."""
        return decode_string(data, strip=True, replace_on_error=False)

    def _read_grid(self, f: BinaryIO, pattern: Pattern) -> None:
        """Liest die Grid-Daten."""

        layer = pattern.active_layer
        if not layer:
            return

        color_count = len(pattern.color_entries)

        # Versuche RLE-komprimierte Daten zu lesen
        try:
            # RLE-Marker prüfen
            marker = f.read(1)

            if marker == b"\xff":
                # RLE-komprimiert
                self._read_rle_grid(f, layer, pattern.width, pattern.height, color_count)
            else:
                # Unkomprimiert - zurücksetzen
                f.seek(-1, 1)
                self._read_raw_grid(f, layer, pattern.width, pattern.height, color_count)

        except (ValueError, IndexError, struct.error) as e:
            self.warnings.append(f"Fehler beim Lesen der Grid-Daten: {e}")

    def _clamp_color_index(self, color_index: int | None, color_count: int) -> int | None:
        """Verwirft einen Farbindex außerhalb der eingelesenen Palette.

        Eine beschädigte/verkürzte Datei kann ein Grid-Byte enthalten, das
        auf einen Farbeintrag zeigt, den die Palette gar nicht hat --
        `Layer.set_stitch()` prüft nur x/y, nicht den Farbindex, würde den
        Wert also klaglos übernehmen. Downstream (Export-Statistiken,
        Rendering) wird ein solcher Stich dann OHNE Warnung als leere
        Zelle behandelt -- betroffene Stiche fehlen dem Nutzer sonst
        stillschweigend.
        """
        if color_index is not None and color_index >= color_count:
            if not self._invalid_color_index_warned:
                self.warnings.append(
                    f"Farbindex {color_index} außerhalb der Palette ({color_count} Farben) "
                    "— betroffene Stiche werden als leer behandelt"
                )
                self._invalid_color_index_warned = True
            return None
        return color_index

    def _read_rle_grid(
        self, f: BinaryIO, layer: Layer, width: int, height: int, color_count: int
    ) -> None:
        """Liest RLE-komprimierte Grid-Daten."""

        x, y = 0, 0

        while y < height:
            byte = f.read(1)
            if not byte:
                break

            value = struct.unpack("B", byte)[0]

            if value == 0xFF:
                # Run-Length
                count = struct.unpack("B", f.read(1))[0]
                color = struct.unpack("B", f.read(1))[0]

                for _ in range(count):
                    if color == 0xFF:
                        color_index = None  # Leer
                    else:
                        color_index = self._clamp_color_index(color, color_count)

                    layer.set_stitch(x, y, color_index)
                    x += 1
                    if x >= width:
                        x = 0
                        y += 1
                        if y >= height:
                            break
            else:
                # Einzelner Stich
                if value == 0xFE:
                    color_index = None
                else:
                    color_index = self._clamp_color_index(value, color_count)

                layer.set_stitch(x, y, color_index)
                x += 1
                if x >= width:
                    x = 0
                    y += 1

    def _read_raw_grid(
        self, f: BinaryIO, layer: Layer, width: int, height: int, color_count: int
    ) -> None:
        """Liest unkomprimierte Grid-Daten."""

        for y in range(height):
            for x in range(width):
                byte = f.read(1)
                if not byte:
                    return

                value = struct.unpack("B", byte)[0]

                if value == 0xFF or value == 0xFE:
                    color_index = None
                else:
                    color_index = self._clamp_color_index(value, color_count)

                layer.set_stitch(x, y, color_index)

    def _read_backstitches(self, f: BinaryIO, pattern: Pattern) -> None:
        """Liest Backstitch-Daten."""

        color_count = len(pattern.color_entries)

        try:
            # Anzahl Backstitches (2 Bytes)
            count_data = f.read(2)
            if len(count_data) < 2:
                return

            count = struct.unpack("<H", count_data)[0]

            for _ in range(count):
                # Koordinaten (8 Bytes: 4x int16)
                coords = f.read(8)
                if len(coords) < 8:
                    break

                x1, y1, x2, y2 = struct.unpack("<hhhh", coords)

                # Farbe (1 Byte)
                color_byte = f.read(1)
                if not color_byte:
                    break

                color_index = struct.unpack("B", color_byte)[0]

                # Farbindex gegen die eingelesene Palette pruefen -- dieselbe
                # Absicherung wie beim Grid (_clamp_color_index), die bislang
                # nur dort griff. Ohne das haette ein korrupter Backstitch-
                # Farbindex klaglos (ohne Warnung) ein Backstitch mit
                # nicht existierendem Farbindex im Pattern hinterlassen.
                clamped = self._clamp_color_index(color_index, color_count)
                if clamped is None:
                    continue

                # Backstitch hinzufügen
                pattern.add_backstitch(x1, y1, x2, y2, clamped)

        except (ValueError, IndexError, struct.error) as e:
            self.warnings.append(f"Fehler beim Lesen der Backstitch-Daten: {e}")


def import_xsd(filepath: Path | str) -> tuple[Pattern | None, list[str], list[str]]:
    """
    Convenience-Funktion zum Importieren einer XSD-Datei.

    Returns:
        (Pattern, Fehler-Liste, Warnungs-Liste)
    """
    importer = XSDImporter()
    pattern = importer.import_file(filepath)
    return pattern, importer.errors, importer.warnings
