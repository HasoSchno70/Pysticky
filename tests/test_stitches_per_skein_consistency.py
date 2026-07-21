# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 12): STITCHES_PER_SKEIN existierte als vier
unabhaengige, hart-codierte Kopien (Statistik-Dialog, PDF-Export,
HTML-Export, Bundle-Export) -- PDF/HTML hatten dabei ~3.6x hoehere Werte
als Statistik-Dialog/Bundle-Export/Einkaufsliste (die schon uebereinstimmten),
sodass derselbe "Garnbedarf" je nach Ansicht stark unterschiedliche Zahlen
zeigte. Jetzt gibt es genau eine Quelle (core.constants.STITCHES_PER_SKEIN),
die alle vier Konsumenten importieren. Dieser Test soll verhindern, dass
ein zukuenftiger Patch versehentlich wieder eine eigene, abweichende Kopie
einfuehrt.
"""

from pysticky.core.constants import STITCHES_PER_SKEIN


def test_pdf_export_uses_shared_constant():
    from pysticky.io import pdf_export

    assert pdf_export.STITCHES_PER_SKEIN is STITCHES_PER_SKEIN


def test_html_export_uses_shared_constant():
    from pysticky.io import html_export

    assert html_export.STITCHES_PER_SKEIN is STITCHES_PER_SKEIN


def test_statistics_tabs_use_shared_constant():
    from pysticky.ui.dialogs.statistics_tabs import _constants

    assert _constants.STITCHES_PER_SKEIN is STITCHES_PER_SKEIN
