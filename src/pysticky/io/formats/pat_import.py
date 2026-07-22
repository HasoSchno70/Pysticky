"""
PAT (PCStitch) Dateiformat-Import.

PCStitch PAT ist ein proprietäres Binärformat.
Diese Implementierung basiert auf Reverse-Engineering und
Community-Dokumentation des Formats.

Unterstützte Features:
- Grid-Daten (Kreuzstiche)
- Farbpalette mit DMC-Nummern
- Rückstiche (Backstitches)
- Metadaten (Titel, Autor, Copyright)

Nicht unterstützt:
- Spezialstiche (French Knots, Beads)
- Eingebettete Bilder
- Erweiterte Stichtypen
"""

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from ...core.constants import DEFAULT_FABRIC_COUNT
from ...core.layer import Layer
from ...core.pattern import ColorEntry, Pattern
from ...core.thread import Thread, ThreadColor
from ._binary import decode_string, read_exact


@dataclass
class PATHeader:
    """PAT-Datei Header-Struktur."""

    signature: bytes
    version: int
    width: int
    height: int
    color_count: int
    fabric_count: int
    title: str
    author: str
    copyright: str


class PATImportError(Exception):
    """Fehler beim Importieren einer PAT-Datei."""

    pass


class PATImporter:
    """
    Importiert PCStitch PAT-Dateien.

    Das PAT-Format hat folgende Struktur:
    - Header mit Signatur "PAT" und Version
    - Metadaten-Block
    - Farbpalette mit DMC-Nummern
    - Grid-Daten
    - Optional: Backstitch, Special Stitches
    """

    # PAT Signatur
    SIGNATURE = b"PAT"

    # Bekannte Versionen
    KNOWN_VERSIONS = [5, 6, 7, 8, 9, 10]

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self._invalid_color_index_warned = False

    def can_import(self, filepath: Path | str) -> bool:
        """Prüft ob die Datei ein PAT-Format ist."""
        filepath = Path(filepath)

        if not filepath.exists():
            return False

        if filepath.suffix.lower() != ".pat":
            return False

        try:
            with open(filepath, "rb") as f:
                signature = f.read(3)
                return signature == self.SIGNATURE
        except OSError:
            return False

    def import_file(self, filepath: Path | str) -> Pattern | None:
        """
        Importiert eine PAT-Datei.

        Args:
            filepath: Pfad zur PAT-Datei

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
                return self._parse_pat(f, filepath.stem)
        except PATImportError as e:
            self.errors.append(str(e))
            return None
        except Exception as e:  # catch-all: format may have unexpected structure
            self.errors.append(f"Unerwarteter Fehler: {e}")
            return None

    def _parse_pat(self, f: BinaryIO, name: str) -> Pattern:
        """Parst den PAT-Dateiinhalt."""

        # Signatur prüfen
        signature = f.read(3)
        if signature != self.SIGNATURE:
            raise PATImportError(f"Ungültige Signatur: {signature!r}")

        # Version (1 Byte)
        version = struct.unpack("B", read_exact(f, 1, "Version"))[0]

        if version not in self.KNOWN_VERSIONS:
            self.warnings.append(f"Unbekannte PAT-Version: {version}")

        # Header lesen
        header = self._read_header(f, version, signature)

        if header.width < 1 or header.height < 1:
            raise PATImportError(f"Ungültige Dimensionen: {header.width}x{header.height}")

        # Width/Height kommen aus einem ungeprüften struct.unpack ("<HH",
        # max. 65535 je Achse) -- ohne Obergrenze könnte eine beschädigte
        # Datei eine ~4,3-Milliarden-Zellen-Allokation auslösen. Gleiche
        # Grenzen wie file_io.py/xsd_import.py/oxs_io.py (harte Grenze).
        if header.width > 2000 or header.height > 2000:
            raise PATImportError(
                f"Mustergröße zu groß: {header.width}x{header.height} (max. 2000x2000)"
            )

        if header.width > 1000 or header.height > 1000:
            self.warnings.append(f"Große Muster-Dimensionen: {header.width}x{header.height}")

        # Pattern erstellen
        pattern = Pattern(
            name=header.title or name,
            width=header.width,
            height=header.height,
            fabric_count=header.fabric_count,
        )
        pattern.color_entries.clear()

        # Metadaten
        if header.author:
            pattern.metadata["author"] = header.author
        if header.copyright:
            pattern.metadata["copyright"] = header.copyright
        pattern.metadata["imported_from"] = "pat"
        pattern.metadata["pat_version"] = version

        # Farbpalette lesen
        self._read_colors(f, pattern, header.color_count, version)

        # Grid-Daten lesen
        self._read_grid(f, pattern, version)

        # Backstitch-Daten lesen
        self._read_backstitches(f, pattern, version)

        # Stichzahlen berechnen
        pattern.recalculate_stitch_counts()

        return pattern

    def _read_header(self, f: BinaryIO, version: int, signature: bytes) -> PATHeader:
        """Liest den PAT-Header."""

        # Format variiert je nach Version
        if version >= 8:
            return self._read_header_v8plus(f, version, signature)
        else:
            return self._read_header_legacy(f, version, signature)

    def _read_header_v8plus(self, f: BinaryIO, version: int, signature: bytes) -> PATHeader:
        """Liest Header für Version 8+."""

        # Header-Größe (4 Bytes) — Wert wird nicht ausgewertet, nur überlesen
        read_exact(f, 4, "Header-Größe")

        # Dimensionen (4 Bytes: 2x uint16)
        width, height = struct.unpack("<HH", read_exact(f, 4, "Dimensionen"))

        # Farbanzahl (2 Bytes)
        color_count = struct.unpack("<H", read_exact(f, 2, "Farbanzahl"))[0]

        # Stoffzählung (2 Bytes)
        fabric_count = struct.unpack("<H", read_exact(f, 2, "Stoffzählung"))[0]
        if fabric_count < 8 or fabric_count > 32:
            fabric_count = DEFAULT_FABRIC_COUNT

        # Titel (variable Länge, Pascal-String)
        title = self._read_pascal_string(f)

        # Author
        author = self._read_pascal_string(f)

        # Copyright
        copyright = self._read_pascal_string(f)

        return PATHeader(
            signature=signature,
            version=version,
            width=width,
            height=height,
            color_count=color_count,
            fabric_count=fabric_count,
            title=title,
            author=author,
            copyright=copyright,
        )

    def _read_header_legacy(self, f: BinaryIO, version: int, signature: bytes) -> PATHeader:
        """Liest Header für ältere Versionen (< 8)."""

        # Dimensionen (4 Bytes)
        width, height = struct.unpack("<HH", read_exact(f, 4, "Dimensionen"))

        # Farbanzahl (2 Bytes)
        color_count = struct.unpack("<H", read_exact(f, 2, "Farbanzahl"))[0]

        # Stoffzählung (1 Byte)
        fabric_count = struct.unpack("B", read_exact(f, 1, "Stoffzählung"))[0]
        if fabric_count < 8 or fabric_count > 32:
            fabric_count = DEFAULT_FABRIC_COUNT

        # Reserved (1 Byte)
        f.read(1)

        # Titel (32 Bytes, null-terminiert)
        title = self._read_fixed_string(f, 32)

        # Author (32 Bytes)
        author = self._read_fixed_string(f, 32)

        # Copyright (32 Bytes)
        copyright = self._read_fixed_string(f, 32)

        return PATHeader(
            signature=signature,
            version=version,
            width=width,
            height=height,
            color_count=color_count,
            fabric_count=fabric_count,
            title=title,
            author=author,
            copyright=copyright,
        )

    def _read_pascal_string(self, f: BinaryIO) -> str:
        """Liest einen Pascal-String (Länge + Daten)."""
        length = struct.unpack("B", f.read(1))[0]
        if length == 0:
            return ""
        # Pascal-Strings sind längenpräfixiert, nicht null-terminiert.
        return decode_string(f.read(length), null_terminated=False)

    def _read_fixed_string(self, f: BinaryIO, length: int) -> str:
        """Liest einen null-terminierten String fester Länge."""
        return decode_string(f.read(length))

    def _read_colors(self, f: BinaryIO, pattern: Pattern, count: int, version: int) -> None:
        """Liest die Farbpalette."""

        symbols = (
            "●○■□▲△◆◇★☆+×/\\~@&%#$!?=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        )

        for i in range(count):
            try:
                # RGB (3 Bytes)
                r, g, b = struct.unpack("BBB", f.read(3))

                # DMC-Nummer (variiert je nach Version)
                if version >= 8:
                    dmc_number = self._read_pascal_string(f)
                    name = self._read_pascal_string(f)
                else:
                    dmc_data = f.read(6)
                    dmc_number = self._read_fixed_string_from_bytes(dmc_data)
                    name_data = f.read(20)
                    name = self._read_fixed_string_from_bytes(name_data)

                if not name:
                    if dmc_number:
                        name = f"DMC {dmc_number}"
                    else:
                        name = f"Farbe {i + 1}"

                # Symbol (1 Byte, optional in neueren Versionen)
                try:
                    sym_byte = struct.unpack("B", f.read(1))[0]
                    if 32 <= sym_byte < 127:
                        symbol = chr(sym_byte)
                    else:
                        symbol = symbols[i % len(symbols)]
                except (struct.error, ValueError, IndexError):
                    symbol = symbols[i % len(symbols)]

                thread = Thread(
                    name=name,
                    color=ThreadColor(r, g, b),
                    manufacturer="DMC" if dmc_number else "",
                    catalog_number=dmc_number,
                )

                entry = ColorEntry(thread=thread, symbol=symbol, stitch_count=0)
                pattern.color_entries.append(entry)

            except (struct.error, ValueError, IndexError) as e:
                self.warnings.append(f"Fehler beim Lesen von Farbe {i}: {e}")
                thread = Thread.from_hex(f"Farbe {i + 1}", "#808080")
                pattern.color_entries.append(
                    ColorEntry(thread=thread, symbol=symbols[i % len(symbols)])
                )

    def _read_fixed_string_from_bytes(self, data: bytes) -> str:
        """Extrahiert String aus Byte-Array."""
        return decode_string(data, strip=True, replace_on_error=False)

    def _read_grid(self, f: BinaryIO, pattern: Pattern, version: int) -> None:
        """Liest die Grid-Daten."""

        layer = pattern.active_layer
        if not layer:
            return

        color_count = len(pattern.color_entries)

        try:
            if version >= 8:
                # Neuere Versionen: Grid-Größe vorangestellt
                grid_size = struct.unpack("<I", f.read(4))[0]
                self._read_compressed_grid(
                    f, layer, pattern.width, pattern.height, grid_size, color_count
                )
            else:
                # Ältere Versionen: Roh
                self._read_raw_grid(f, layer, pattern.width, pattern.height, color_count)

        except (struct.error, ValueError, IndexError) as e:
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

    def _read_compressed_grid(
        self,
        f: BinaryIO,
        layer: Layer,
        width: int,
        height: int,
        expected_size: int,
        color_count: int,
    ) -> None:
        """Liest komprimierte Grid-Daten."""

        x, y = 0, 0
        bytes_read = 0

        while y < height and bytes_read < expected_size:
            byte = f.read(1)
            if not byte:
                break
            bytes_read += 1

            value = struct.unpack("B", byte)[0]

            if value & 0x80:
                # High-Bit gesetzt: Run-Length Encoding
                count = value & 0x7F
                color_byte = f.read(1)
                if not color_byte:
                    break
                bytes_read += 1

                color = struct.unpack("B", color_byte)[0]
                color_index = self._clamp_color_index(None if color == 0xFF else color, color_count)

                for _ in range(count):
                    if y >= height:
                        break
                    layer.set_stitch(x, y, color_index)
                    x += 1
                    if x >= width:
                        x = 0
                        y += 1
            else:
                # Einzelner Stich
                color_index = self._clamp_color_index(None if value == 0xFF else value, color_count)
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
            row_data = f.read(width)
            if len(row_data) < width:
                self.warnings.append(f"Unvollständige Zeile {y}")
                break

            for x, value in enumerate(row_data):
                color_index = self._clamp_color_index(None if value == 0xFF else value, color_count)
                layer.set_stitch(x, y, color_index)

    def _read_backstitches(self, f: BinaryIO, pattern: Pattern, version: int) -> None:
        """Liest Backstitch-Daten."""

        try:
            # Prüfe ob noch Daten vorhanden
            pos = f.tell()
            test = f.read(4)
            if len(test) < 4:
                return
            f.seek(pos)

            # Anzahl Backstitches
            count = struct.unpack("<I", f.read(4))[0]

            if count > 10000:
                self.warnings.append(f"Ungewöhnlich viele Backstitches: {count}")
                return

            for _ in range(count):
                # Koordinaten (8 Bytes: 4x int16)
                coords_data = f.read(8)
                if len(coords_data) < 8:
                    break

                x1, y1, x2, y2 = struct.unpack("<hhhh", coords_data)

                # Farbe (2 Bytes in neueren, 1 Byte in älteren Versionen)
                if version >= 8:
                    color_index = struct.unpack("<H", f.read(2))[0]
                else:
                    color_index = struct.unpack("B", f.read(1))[0]

                # In halbe Stiche konvertieren (PAT verwendet ganze Koordinaten)
                pattern.add_backstitch(x1 * 2, y1 * 2, x2 * 2, y2 * 2, color_index)

        except (struct.error, ValueError, IndexError) as e:
            self.warnings.append(f"Fehler beim Lesen der Backstitch-Daten: {e}")


def import_pat(filepath: Path | str) -> tuple[Pattern | None, list[str], list[str]]:
    """
    Convenience-Funktion zum Importieren einer PAT-Datei.

    Returns:
        (Pattern, Fehler-Liste, Warnungs-Liste)
    """
    importer = PATImporter()
    pattern = importer.import_file(filepath)
    return pattern, importer.errors, importer.warnings
