# Build standalone Windows .exe and zip for distribution.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$DistExe = Join-Path $Root "dist\MIK-to-Rekordbox.exe"
$ZipPath = Join-Path $Root "dist\MIK-to-Rekordbox-win64.zip"
$Readme = Join-Path $Root "packaging\windows\README.txt"

if (-not (Test-Path $VenvPython)) {
    python -m venv .venv
}

& $VenvPython -m pip install --upgrade pip -q
& $VenvPython -m pip install -r requirements.txt -q
& $VenvPython -m pip install pyinstaller -q

& $VenvPython -c "import tkinter; print('tkinter OK')"

if (Test-Path (Join-Path $Root "dist")) {
    Remove-Item -Recurse -Force (Join-Path $Root "dist")
}
if (Test-Path (Join-Path $Root "build")) {
    Remove-Item -Recurse -Force (Join-Path $Root "build\MIK-to-Rekordbox") -ErrorAction SilentlyContinue
}

& $VenvPython -m PyInstaller --noconfirm mik_sync.spec

if (-not (Test-Path $DistExe)) {
    throw "PyInstaller did not produce $DistExe"
}

$Stage = Join-Path $Root "build\win-release"
if (Test-Path $Stage) { Remove-Item -Recurse -Force $Stage }
New-Item -ItemType Directory -Path $Stage | Out-Null
Copy-Item $DistExe $Stage
Copy-Item $Readme (Join-Path $Stage "README.txt")

if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }
Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $ZipPath

Write-Host ""
Write-Host "Release build complete:"
Write-Host "  Exe: $DistExe"
Write-Host "  Zip: $ZipPath"
