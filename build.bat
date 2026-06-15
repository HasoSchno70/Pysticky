@echo off
REM ============================================
REM PySticky Build Script für Windows
REM ============================================

echo.
echo ========================================
echo    PySticky Build Script
echo ========================================
echo.

REM Prüfen ob PyInstaller installiert ist
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] PyInstaller wird installiert...
    pip install pyinstaller
    if errorlevel 1 (
        echo [FEHLER] PyInstaller konnte nicht installiert werden!
        pause
        exit /b 1
    )
)

REM Alte Builds löschen
echo [INFO] Räume alte Builds auf...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

REM Build starten
echo.
echo [INFO] Starte Build-Prozess...
echo.

pyinstaller pysticky.spec --noconfirm

if errorlevel 1 (
    echo.
    echo [FEHLER] Build fehlgeschlagen!
    pause
    exit /b 1
)

echo.
echo ========================================
echo    Build erfolgreich!
echo ========================================
echo.
echo Die ausführbare Datei befindet sich in:
echo    dist\PySticky.exe
echo.
echo Größe:
for %%A in (dist\PySticky.exe) do echo    %%~zA Bytes (ca. %%~zA bytes)
echo.

REM Optional: dist-Ordner öffnen
explorer dist

pause
