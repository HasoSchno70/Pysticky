# PySticky Build-Anleitung

*Deutsch | [English](BUILD.en.md)*

## Voraussetzungen

- Python 3.10+ installiert
- Alle Abhängigkeiten installiert (`pip install -r requirements.txt`)
- PyInstaller (`pip install pyinstaller`)

## Schnellstart

### Option 1: PowerShell (empfohlen)
```powershell
.\build.ps1
```

### Option 2: Batch-Datei
```cmd
build.bat
```

### Option 3: Manuell
```powershell
# PyInstaller installieren
pip install pyinstaller

# Build starten
pyinstaller pysticky.spec --noconfirm
```

## Ergebnis

Nach erfolgreichem Build findest du die ausführbare Datei unter:
```
dist\PySticky.exe
```

Die Datei ist ca. 80-120 MB groß (enthält Python + PySide6/Qt).

## Problembehebung

### "ModuleNotFoundError"
Falls Module fehlen, füge sie in `pysticky.spec` unter `hiddenimports` hinzu:
```python
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui', 
    'PySide6.QtWidgets',
    'fehlendes_modul',  # Hier hinzufügen
]
```

### Ressourcen fehlen
Falls Paletten oder Styles fehlen, prüfe den `datas`-Abschnitt in `pysticky.spec`.

### Antivirus-Warnung
Manche Antivirus-Programme markieren PyInstaller-EXEs als verdächtig. Das ist ein bekanntes Problem und ein False Positive.

### Kleinere EXE-Größe

1. **UPX Kompression** (bereits aktiviert in spec):
   ```powershell
   # UPX installieren: https://github.com/upx/upx/releases
   # In PATH hinzufügen, dann wird es automatisch verwendet
   ```

2. **Virtuelle Umgebung verwenden**:
   ```powershell
   python -m venv .venv_build
   .\.venv_build\Scripts\Activate.ps1
   pip install PySide6 pyinstaller
   # Nur benötigte Pakete = kleinere EXE
   ```

## Alternative: Nuitka (beste Performance)

Nuitka kompiliert Python zu echtem C-Code:

```powershell
pip install nuitka

nuitka --standalone --onefile --enable-plugin=pyside6 ^
       --windows-disable-console ^
       --output-dir=dist ^
       src/pysticky/main.py
```

Vorteile:
- Schnellere Ausführung
- Schwerer zu dekompilieren
- Oft kleinere Dateigröße

Nachteile:
- Längere Build-Zeit
- Benötigt C-Compiler (Visual Studio Build Tools)

## Verteilung

Die `PySticky.exe` kann direkt weitergegeben werden. Sie enthält:
- Python-Runtime
- PySide6/Qt-Bibliotheken
- Alle Ressourcen (Paletten, Styles)

Kein Python muss auf dem Zielrechner installiert sein.
