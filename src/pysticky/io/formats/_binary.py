"""
Gemeinsame Hilfsfunktionen für die binären Format-Importer (PAT, XSD).

Die alten PCStitch- (PAT) und Pattern-Maker- (XSD) Formate sind
reverse-engineert. Beide verwenden Windows-1252 (cp1252) für Strings und
feste Byte-Layouts. Diese Helfer bündeln die zuvor mehrfach duplizierte
Decode- und Längenprüf-Logik an einer Stelle.
"""

from __future__ import annotations

from typing import BinaryIO


def decode_string(
    data: bytes,
    *,
    null_terminated: bool = True,
    strip: bool = False,
    replace_on_error: bool = True,
) -> str:
    """Dekodiert Bytes aus einem reverse-engineerten Binärformat.

    Die Formate speichern Strings in Windows-1252 (cp1252). Bei ungültigen
    Bytes wird wahlweise auf Latin-1 zurückgegriffen (verlustfrei pro Byte)
    oder ein leerer String geliefert.

    Args:
        data: Rohbytes.
        null_terminated: Schneidet am ersten Null-Byte ab (C-Strings).
        strip: Entfernt führende/abschließende Whitespaces.
        replace_on_error: True → Latin-1-Fallback, False → "" bei Decode-Fehler.
    """
    if null_terminated:
        null_pos = data.find(b"\x00")
        if null_pos >= 0:
            data = data[:null_pos]
    try:
        text = data.decode("cp1252")
    except (UnicodeDecodeError, ValueError):
        if not replace_on_error:
            return ""
        text = data.decode("latin-1", errors="replace")
    return text.strip() if strip else text


def read_exact(f: BinaryIO, size: int, what: str = "Daten") -> bytes:
    """Liest genau ``size`` Bytes oder wirft EOFError bei abgeschnittener Datei.

    Liefert eine klare Fehlermeldung statt eines rohen ``struct.error``, wenn
    eine Datei mitten in einem Feld fester Länge (z. B. dem Header) endet.

    Args:
        f: Geöffneter Binär-Stream.
        size: Erwartete Byte-Anzahl.
        what: Bezeichnung des Felds für die Fehlermeldung.
    """
    data = f.read(size)
    if len(data) < size:
        raise EOFError(
            f"Datei zu kurz beim Lesen von {what}: erwartet {size} Bytes, erhalten {len(data)}"
        )
    return data
