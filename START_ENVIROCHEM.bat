@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title EnviroChem Studio v2.23.0 Alpha 3.2.2

echo ==================================================
echo EnviroChem Studio v2.23.0 Alpha 3.2.2 startup
echo ==================================================
echo.
echo The startup console will remain visible so that any error can be read.
echo Startup details are also saved to STARTUP_LOG.txt.
echo.

if not exist "%~dp0START_ENVIROCHEM_CONSOLE.cmd" (
  echo ERROR: START_ENVIROCHEM_CONSOLE.cmd is missing.
  echo Extract the complete ZIP to a normal folder before starting EnviroChem.
  echo Do not run this file from inside the ZIP preview.
  pause
  exit /b 1
)

call "%~dp0START_ENVIROCHEM_CONSOLE.cmd"
set "ENVIROCHEM_EXIT=%ERRORLEVEL%"

if not "%ENVIROCHEM_EXIT%"=="0" (
  echo.
  echo EnviroChem startup returned error code %ENVIROCHEM_EXIT%.
  if exist "%~dp0STARTUP_LOG.txt" start "" notepad "%~dp0STARTUP_LOG.txt"
  echo If requesting help, send STARTUP_LOG.txt.
  pause
)

exit /b %ENVIROCHEM_EXIT%
