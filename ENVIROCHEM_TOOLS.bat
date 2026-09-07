@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "PORT=8792"
if defined ENVIROCHEM_PORT set "PORT=%ENVIROCHEM_PORT%"
if not defined ENVIROCHEM_PORT if exist ".venv\Scripts\python.exe" (
  set "PORT_FILE=%TEMP%\envirochem_tools_port_%RANDOM%_%RANDOM%.txt"
  ".venv\Scripts\python.exe" -m app.launcher_support configured-port > "!PORT_FILE!" 2>nul
  if not errorlevel 1 set /p "PORT="<"!PORT_FILE!"
  if exist "!PORT_FILE!" del /q "!PORT_FILE!"
)

:menu
cls
echo ==================================================
echo EnviroChem Studio v2.23 support tools
echo Runtime port: %PORT%
echo ==================================================
echo 1. Run startup diagnostics
echo 2. Open build verification page
echo 3. Check FOCUS installation folders
echo 4. Reset local Python environment
echo 5. Reset local database
echo 6. Open startup log
echo 7. Exit
choice /c 1234567 /n /m "Choose an action: "
if errorlevel 7 exit /b 0
if errorlevel 6 goto :open_log
if errorlevel 5 goto :reset_database
if errorlevel 4 goto :reset_python
if errorlevel 3 goto :focus
if errorlevel 2 goto :verify
if errorlevel 1 goto :diagnose

:diagnose
set "LOG=%CD%\STARTUP_DIAGNOSTIC.txt"
>"%LOG%" echo EnviroChem Studio v2.23 diagnostic
>>"%LOG%" echo Date: %DATE% %TIME%
>>"%LOG%" echo Folder: %CD%
>>"%LOG%" echo Runtime port: %PORT%
>>"%LOG%" echo.
where python >>"%LOG%" 2>&1
python --version >>"%LOG%" 2>&1
where py >>"%LOG%" 2>&1
py -0p >>"%LOG%" 2>&1
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" --version >>"%LOG%" 2>&1
  ".venv\Scripts\python.exe" -m pip --version >>"%LOG%" 2>&1
  ".venv\Scripts\python.exe" -c "import fastapi,uvicorn,sqlalchemy,pydantic,httpx,pypdf,numpy; from app.config import settings; print('Core imports and settings OK')" >>"%LOG%" 2>&1
) else (
  >>"%LOG%" echo No local Python environment exists yet. Run START_ENVIROCHEM.bat.
)
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort %PORT% -ErrorAction SilentlyContinue | Format-List *" >>"%LOG%" 2>&1
start "" notepad "%LOG%"
goto :menu

:verify
start "" "http://127.0.0.1:%PORT%/api/build"
goto :menu

:focus
echo.
for %%A in ("C:\Program Files (x86)\Pesticide Models\SPIN" "C:\Program Files (x86)\Pesticide Models\FOCUSPEARL" "C:\SWASH" "C:\SWASH\MACRO" "C:\SWASH\TOXSWA") do (
  if exist %%~A (echo [FOUND] %%~A) else (echo [MISSING] %%~A)
)
echo Custom paths: ENVIROCHEM_SPIN_PATH, ENVIROCHEM_PEARL_PATH,
echo ENVIROCHEM_SWASH_PATH, ENVIROCHEM_MACRO_PATH and ENVIROCHEM_TOXSWA_PATH.
echo GREAT-ER can be configured separately with ENVIROCHEM_GREATER_PATH.
pause
goto :menu

:reset_python
echo.
echo This removes only .venv and local startup logs. Project data is preserved.
set /p "CONFIRM=Type RESET PYTHON to continue: "
if /i not "%CONFIRM%"=="RESET PYTHON" goto :menu
if exist ".venv" rmdir /s /q ".venv"
if exist "STARTUP_LOG.txt" del /q "STARTUP_LOG.txt"
if exist "STARTUP_DIAGNOSTIC.txt" del /q "STARTUP_DIAGNOSTIC.txt"
echo Python environment reset. Run START_ENVIROCHEM.bat to rebuild it.
pause
goto :menu

:reset_database
echo.
echo This permanently removes local projects, model runs and audit history.
set /p "CONFIRM=Type DELETE LOCAL DATA to continue: "
if /i not "%CONFIRM%"=="DELETE LOCAL DATA" goto :menu
if exist "data\envirochem.sqlite" del /q "data\envirochem.sqlite"
echo Local database removed. A fresh database will be created on next start.
pause
goto :menu

:open_log
if exist "STARTUP_LOG.txt" (start "" notepad "STARTUP_LOG.txt") else (echo No startup log exists yet. & pause)
goto :menu
