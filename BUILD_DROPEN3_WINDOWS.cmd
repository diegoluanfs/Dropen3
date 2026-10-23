@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Dropen3 v1.2.0.dev0 - Windows Build

echo ==========================================================
echo   DROPEN3 v1.2.0.dev0 - WINDOWS EXECUTABLE BUILD
 echo ==========================================================
echo.
if not exist "pyproject.toml" (
    echo ERROR: pyproject.toml not found in this directory.
    goto :failed
)
if not exist "packaging\build_windows.ps1" (
    echo ERROR: packaging\build_windows.ps1 not found.
    goto :failed
)
where py >nul 2>&1
if errorlevel 1 (
    echo ERROR: The Python launcher was not found.
    echo Install Python 3.12 for Windows and enable the Python launcher.
    goto :failed
)
py -3.12 --version
if errorlevel 1 (
    echo ERROR: Python 3.12 is not installed or is unavailable.
    goto :failed
)

echo.
echo Running automated tests and building standalone executables...
echo This build uses the local venv and tests before packaging.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0packaging\build_windows.ps1"
if errorlevel 1 goto :failed

if not exist "dist\Dropen3.exe" (
    echo ERROR: Build exited successfully but dist\Dropen3.exe is missing.
    goto :failed
)
if not exist "dist\Dropen3Doctor.exe" (
    echo ERROR: Build exited successfully but dist\Dropen3Doctor.exe is missing.
    goto :failed
)
echo.
echo SUCCESS: Windows executable files have been generated.
echo   %CD%\dist\Dropen3.exe
echo   %CD%\dist\Dropen3Doctor.exe
echo.
echo Confirm zoom-in, zoom-out at the maximum limit, Fit,
echo A/D, arrow keys, and Doctor on this Windows computer.
echo.
pause
exit /b 0

:failed
echo.
echo BUILD FAILED. Review the errors above and fix them before distribution.
echo The terminal will remain open for inspection.
echo.
pause
exit /b 1
