# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec-Datei für PySticky.

Erstellt mit: pyinstaller pysticky.spec
"""

import sys
from pathlib import Path

block_cipher = None

# Projektpfade
PROJECT_ROOT = Path(SPECPATH)
SRC_PATH = PROJECT_ROOT / 'src'
RESOURCES_PATH = SRC_PATH / 'pysticky' / 'resources'

# Daten-Dateien (Paletten, Styles, Icons, i18n, Built-in-Plugins)
PLUGINS_PATH = SRC_PATH / 'pysticky' / 'plugins' / 'builtin'
datas = [
    (str(RESOURCES_PATH / 'palettes'), 'pysticky/resources/palettes'),
    (str(RESOURCES_PATH / 'styles'), 'pysticky/resources/styles'),
    (str(RESOURCES_PATH / 'icons'), 'pysticky/resources/icons'),
    (str(RESOURCES_PATH / 'i18n'), 'pysticky/resources/i18n'),
    (str(RESOURCES_PATH / 'symbols.txt'), 'pysticky/resources'),
    (str(PLUGINS_PATH), 'pysticky/plugins/builtin'),
]

# Icon-Pfad für die EXE
ICON_PATH = str(RESOURCES_PATH / 'icons' / 'sticken.ico')

# Versteckte Imports (falls nötig)
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui', 
    'PySide6.QtWidgets',
]

a = Analysis(
    ['pysticky_main.py'],
    pathex=[str(SRC_PATH)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'pandas',
        'scipy',
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PySticky',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False = kein Konsolenfenster (Release)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_PATH,  # PySticky Icon
)
