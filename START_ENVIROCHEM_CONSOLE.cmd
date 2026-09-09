@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "PORT=8792"
if defined ENVIROCHEM_PORT set "PORT=%ENVIROCHEM_PORT%"
set "BUILD=envirochem-studio-v2.23.0-alpha3.4.0-applied-environmental-fate-2026-09-09"
set "LOG=%CD%\STARTUP_LOG.txt"
set "VENV_PY=%CD%\.venv\Scripts\python.exe"
set "READY_MARKER=%CD%\.venv\.envirochem_core_ready_v223a3"

> "%LOG%" echo EnviroChem Studio v2.23.0 Alpha 3.4.0 startup log
>>"%LOG%" echo Started: %DATE% %TIME%
>>"%LOG%" echo Folder: %CD%

echo ==================================================
echo EnviroChem Studio v2.23.0 Alpha 3.4.0
echo US EPA execution bridge, groundwater screen and tier-safe model routing
echo ==================================================
echo.
echo Native Python RDKit is NOT required for normal startup.
echo EnviroDesign uses RDKit.js/WebAssembly in the browser.
echo.

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 (
  for %%V in (3.14 3.13 3.12 3.11 3.10) do (
    if not defined PYTHON_CMD (
      py -%%V -c "import sys; print(sys.executable)" >nul 2>nul
      if not errorlevel 1 set "PYTHON_CMD=py -%%V"
    )
  )
)
if not defined PYTHON_CMD (
  where python >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
  echo ERROR: Python was not found.
  echo Install Python 3.10-3.14, then run this launcher again.
  >>"%LOG%" echo ERROR: Python was not found.
  pause
  exit /b 1
)

%PYTHON_CMD% --version
%PYTHON_CMD% --version >>"%LOG%" 2>&1

if exist "%VENV_PY%" (
  "%VENV_PY%" -c "import sys; print(sys.version)" >>"%LOG%" 2>&1
  if errorlevel 1 (
    echo Existing virtual environment is damaged. Rebuilding it...
    rmdir /s /q ".venv"
  )
)

if not exist "%VENV_PY%" (
  echo Creating local Python environment...
  %PYTHON_CMD% -m venv .venv >>"%LOG%" 2>&1
  if errorlevel 1 goto :install_error
)

if not exist "%READY_MARKER%" (
  echo Installing core dependencies...
  "%VENV_PY%" -m pip install --upgrade pip setuptools wheel >>"%LOG%" 2>&1
  if errorlevel 1 goto :install_error
  "%VENV_PY%" -m pip install --prefer-binary -r requirements.txt >>"%LOG%" 2>&1
  if errorlevel 1 goto :install_error

  echo Verifying core runtime imports...
  "%VENV_PY%" -c "import fastapi,uvicorn,sqlalchemy,pydantic,httpx,pypdf,numpy; from app.config import settings; print('Core imports and settings OK')" >>"%LOG%" 2>&1
  if errorlevel 1 goto :import_error
  type nul > "%READY_MARKER%"
) else (
  echo Core dependencies already prepared.
)

if not defined ENVIROCHEM_PORT (
  set "PORT_FILE=%TEMP%\envirochem_port_%RANDOM%_%RANDOM%.txt"
  "%VENV_PY%" -m app.launcher_support configured-port > "!PORT_FILE!" 2>>"%LOG%"
  if not errorlevel 1 set /p "PORT="<"!PORT_FILE!"
  if exist "!PORT_FILE!" del /q "!PORT_FILE!"
)
echo Runtime port: %PORT%  ^(set ENVIROCHEM_PORT or use .env to override^)
>>"%LOG%" echo Resolved runtime port: %PORT%

if not exist "data" mkdir "data"

set "URL=http://127.0.0.1:%PORT%/?build=%BUILD%"
"%VENV_PY%" -m app.launcher_support port-available --port %PORT% >>"%LOG%" 2>&1
if errorlevel 1 (
  "%VENV_PY%" -m app.launcher_support probe-build --port %PORT% --build "%BUILD%" >>"%LOG%" 2>&1
  if not errorlevel 1 (
    echo EnviroChem is already running on port %PORT%. Opening it now...
    >>"%LOG%" echo Existing matching EnviroChem instance reused on port %PORT%.
    start "" "%URL%"
    exit /b 0
  )

  echo Port %PORT% is occupied by another application. Looking for an unused port...
  set "PORT_FILE=%TEMP%\envirochem_port_%RANDOM%_%RANDOM%.txt"
  "%VENV_PY%" -m app.launcher_support find-port --start %PORT% --attempts 50 > "!PORT_FILE!" 2>>"%LOG%"
  if errorlevel 1 (
    if exist "!PORT_FILE!" del /q "!PORT_FILE!"
    echo ERROR: No unused local port was found after %PORT%.
    echo Close the process using that port or set ENVIROCHEM_PORT to another unused port.
    pause
    exit /b 1
  )
  set /p "PORT="<"!PORT_FILE!"
  if exist "!PORT_FILE!" del /q "!PORT_FILE!"
  set "ENVIROCHEM_PORT=!PORT!"
  set "URL=http://127.0.0.1:!PORT!/?build=%BUILD%"
  echo Using port !PORT! instead.
  >>"%LOG%" echo Occupied configured port; selected alternate port !PORT!.
)

echo Starting EnviroChem...
echo The browser opens after the health check passes.
>>"%LOG%" echo Starting server at %URL%
>>"%LOG%" echo Browser readiness helper started without a shared log handle.

rem The background readiness helper must not inherit STARTUP_LOG.txt. On Windows,
rem that shared handle prevents the foreground Uvicorn process opening the log.
start "" /b "%VENV_PY%" -m app.launcher_support open-when-ready --port %PORT% --url "%URL%" --timeout 180 >nul 2>&1

"%VENV_PY%" -m uvicorn app.main:app --host 127.0.0.1 --port %PORT% >>"%LOG%" 2>&1
set "SERVER_EXIT=%ERRORLEVEL%"

echo.
if not "%SERVER_EXIT%"=="0" (
  echo EnviroChem stopped because the server reported an error.
  start "" notepad "%LOG%"
) else (
  echo EnviroChem stopped normally.
)
pause
exit /b %SERVER_EXIT%

:install_error
echo ERROR: Python environment or dependency installation failed.
start "" notepad "%LOG%"
pause
exit /b 1

:import_error
echo ERROR: A CORE dependency could not be loaded.
echo Native RDKit is optional and is not part of this core startup check.
start "" notepad "%LOG%"
pause
exit /b 1
