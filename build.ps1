# ============================================
# PySticky Build Script für Windows (PowerShell)
# ============================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   PySticky Build Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Virtuelle Umgebung aktivieren falls vorhanden
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "[INFO] Aktiviere virtuelle Umgebung..." -ForegroundColor Yellow
    & .\.venv\Scripts\Activate.ps1
}

# Prüfen ob PyInstaller installiert ist
$pyinstaller = pip show pyinstaller 2>$null
if (-not $pyinstaller) {
    Write-Host "[INFO] PyInstaller wird installiert..." -ForegroundColor Yellow
    pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FEHLER] PyInstaller konnte nicht installiert werden!" -ForegroundColor Red
        Read-Host "Drücke Enter zum Beenden"
        exit 1
    }
}

# Alte Builds löschen
Write-Host "[INFO] Räume alte Builds auf..." -ForegroundColor Yellow
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

# __pycache__ löschen für sauberen Build
Write-Host "[INFO] Lösche Cache-Dateien..." -ForegroundColor Yellow
Get-ChildItem -Path "src" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

# Build starten
Write-Host ""
Write-Host "[INFO] Starte Build-Prozess..." -ForegroundColor Green
Write-Host ""

pyinstaller pysticky.spec --noconfirm

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[FEHLER] Build fehlgeschlagen!" -ForegroundColor Red
    Read-Host "Drücke Enter zum Beenden"
    exit 1
}

# Erfolg
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   Build erfolgreich!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

$exePath = "dist\PySticky.exe"
if (Test-Path $exePath) {
    $size = (Get-Item $exePath).Length
    $sizeMB = [math]::Round($size / 1MB, 2)
    Write-Host "Ausführbare Datei: $exePath" -ForegroundColor Cyan
    Write-Host "Größe: $sizeMB MB ($size Bytes)" -ForegroundColor Cyan
    Write-Host ""
    
    # Fragen ob öffnen
    $open = Read-Host "dist-Ordner öffnen? (j/n)"
    if ($open -eq "j" -or $open -eq "J") {
        explorer dist
    }
}

Write-Host ""
Read-Host "Drücke Enter zum Beenden"
