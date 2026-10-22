@echo off
setlocal
set "DOCTOR_PATH=%~dp0Dropen3Doctor.exe"
title Dropen3 System Doctor

if not exist "%DOCTOR_PATH%" (
    echo ERROR: Dropen3Doctor.exe is not in the same directory as this launcher.
    echo.
    pause
    exit /b 2
)

"%DOCTOR_PATH%" --no-pause %*
set "DOCTOR_EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%DOCTOR_EXIT_CODE%"=="0" (
    echo Doctor exited with status %DOCTOR_EXIT_CODE%.
)
echo Press any key to close the Doctor window.
pause >nul
exit /b %DOCTOR_EXIT_CODE%
