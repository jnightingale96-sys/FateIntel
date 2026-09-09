@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title FateIntel v2.24.0 Alpha 4

echo ==================================================
echo FateIntel v2.24.0 Alpha 4 startup
echo ==================================================
echo.
echo The startup console will remain visible so that any error can be read.
echo Startup details are also saved to STARTUP_LOG.txt.
echo.

if not exist "%~dp0START_ENVIROCHEM_CONSOLE.cmd" (
  echo ERROR: The FateIntel console launcher is missing.
  echo Extract the complete ZIP to a short, normal folder before starting FateIntel.
  echo Do not run this file from inside the ZIP preview.
  pause
  exit /b 1
)

call "%~dp0START_ENVIROCHEM_CONSOLE.cmd"
set "FATEINTEL_EXIT=%ERRORLEVEL%"

if not "%FATEINTEL_EXIT%"=="0" (
  echo.
  echo FateIntel startup returned error code %FATEINTEL_EXIT%.
  if exist "%~dp0STARTUP_LOG.txt" start "" notepad "%~dp0STARTUP_LOG.txt"
  echo If requesting help, send STARTUP_LOG.txt.
  pause
)

exit /b %FATEINTEL_EXIT%
