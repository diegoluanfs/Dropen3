$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Root

if (-not (Test-Path '.venv/Scripts/python.exe')) {
  py -3.12 -m venv .venv
}
$Python = Join-Path $Root '.venv/Scripts/python.exe'
& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed' }
& $Python -m pip install -e '.[test,build]'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed. Packaging stopped.' }

$Icon = Join-Path $Root 'src/dropen3/assets/dropen3.ico'
& $Python -m PyInstaller --noconfirm --clean --onefile --windowed --name 'Dropen3' `
 --icon $Icon --paths (Join-Path $Root 'src') `
 --collect-all customtkinter --collect-data dropen3 `
 --hidden-import tkinter --hidden-import PIL._tkinter_finder `
 'src/dropen3/__main__.py'
if ($LASTEXITCODE -ne 0) { throw 'GUI build failed' }

& $Python -m PyInstaller --noconfirm --clean --onefile --console --name 'Dropen3Doctor' `
 --icon $Icon --paths (Join-Path $Root 'src') `
 --collect-all customtkinter --collect-data dropen3 `
 --hidden-import tkinter --hidden-import PIL._tkinter_finder `
 'packaging/doctor_entry.py'
if ($LASTEXITCODE -ne 0) { throw 'Doctor build failed' }
Copy-Item (Join-Path $Root 'packaging/Dropen3Doctor.cmd') (Join-Path $Root 'dist/Dropen3Doctor.cmd') -Force
Write-Host 'Built dist/Dropen3.exe, dist/Dropen3Doctor.exe, and dist/Dropen3Doctor.cmd'
Write-Host 'Run: .\dist\Dropen3Doctor.exe --json --output diagnostic.json'
Write-Host 'Run GUI smoke tests on a clean Windows machine before distributing.'

Write-Host 'For manual use, double-click Dropen3Doctor.exe or Dropen3Doctor.cmd.'
