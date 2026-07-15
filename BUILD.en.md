# PySticky Build Guide

*[Deutsch](BUILD.md) | English*

## Prerequisites

- Python 3.10+ installed
- All dependencies installed (`pip install -r requirements.txt`)
- PyInstaller (`pip install pyinstaller`)

## Quick Start

### Option 1: PowerShell (recommended)
```powershell
.\build.ps1
```

### Option 2: Batch file
```cmd
build.bat
```

### Option 3: Manual
```powershell
# Install PyInstaller
pip install pyinstaller

# Start the build
pyinstaller pysticky.spec --noconfirm
```

## Result

After a successful build you'll find the executable at:
```
dist\PySticky.exe
```

The file is approximately 80-120 MB in size (contains Python + PySide6/Qt).

## Troubleshooting

### "ModuleNotFoundError"
If modules are missing, add them to `pysticky.spec` under `hiddenimports`:
```python
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui', 
    'PySide6.QtWidgets',
    'missing_module',  # Add here
]
```

### Missing resources
If palettes or styles are missing, check the `datas` section in
`pysticky.spec`.

### Antivirus warning
Some antivirus programs flag PyInstaller EXEs as suspicious. This is a known
issue and a false positive.

### Smaller EXE size

1. **UPX compression** (already enabled in the spec):
   ```powershell
   # Install UPX: https://github.com/upx/upx/releases
   # Add it to PATH, then it will be used automatically
   ```

2. **Use a virtual environment**:
   ```powershell
   python -m venv .venv_build
   .\.venv_build\Scripts\Activate.ps1
   pip install PySide6 pyinstaller
   # Only needed packages = smaller EXE
   ```

## Alternative: Nuitka (best performance)

Nuitka compiles Python to real C code:

```powershell
pip install nuitka

nuitka --standalone --onefile --enable-plugin=pyside6 ^
       --windows-disable-console ^
       --output-dir=dist ^
       src/pysticky/main.py
```

Advantages:
- Faster execution
- Harder to decompile
- Often smaller file size

Disadvantages:
- Longer build time
- Requires a C compiler (Visual Studio Build Tools)

## Distribution

The `PySticky.exe` can be distributed directly. It contains:
- Python runtime
- PySide6/Qt libraries
- All resources (palettes, styles)

No Python needs to be installed on the target machine.

## Publishing a Release (GitHub)

Pushing a version tag automatically triggers a build **and** a GitHub
Release with the `.exe` attached as a downloadable asset, via CI
(`.github/workflows/ci.yml`):

```powershell
git tag v0.9.0
git push origin v0.9.0
```

Without a tag push, CI still builds the `.exe` on every push to `main`,
but only as a temporary Actions artifact (expires after ~90 days, only
visible with repo access) — not a public download link.
