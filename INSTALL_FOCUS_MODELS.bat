@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "DL=%~dp0focus_downloads"
if not exist "%DL%" mkdir "%DL%"

echo =============================================================
echo EnviroChem FOCUS installation assistant
echo Official packages are downloaded from European Commission JRC.
echo The packages are NOT bundled or rebranded by EnviroChem.
echo =============================================================
echo.

echo [1/5] Downloading FOCUS SPIN 4.4...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing 'https://esdac.jrc.ec.europa.eu/public_path//projects_data/focus/sw/models/spin/Latest/FOCUS_SPIN_4.4-and-Readmefile.zip' -OutFile '%DL%\FOCUS_SPIN_4.4.zip'"
if errorlevel 1 goto :download_error

echo [2/5] Downloading FOCUS PEARL 5.5.5...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing 'https://esdac.jrc.ec.europa.eu/public_path/projects_data/focus/gw/models/pearl/FOCUSPEARL_5.5.5_September2021.zip' -OutFile '%DL%\FOCUS_PEARL_5.5.5.zip'"
if errorlevel 1 goto :download_error

echo [3/5] Downloading FOCUS SWASH 5.3...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing 'https://esdac.jrc.ec.europa.eu/public_path/projects_data/focus/sw/models/swash/Latest/FOCUS_SWASH5.3.zip' -OutFile '%DL%\FOCUS_SWASH_5.3.zip'"
if errorlevel 1 goto :download_error

echo [4/5] Downloading FOCUS MACRO 5.5.4a...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing 'https://esdac.jrc.ec.europa.eu/public_path//projects_data/focus/gw/software/FOCUS_MACRO_5_5_4a.zip' -OutFile '%DL%\FOCUS_MACRO_5.5.4a.zip'"
if errorlevel 1 goto :download_error

echo [5/5] Downloading FOCUS TOXSWA 5.5.3...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing 'https://esdac.jrc.ec.europa.eu/public_path/projects_data/focus/sw/models/toxswa/Latest/FOCUSTOXSWA_553.zip' -OutFile '%DL%\FOCUS_TOXSWA_5.5.3.zip'"
if errorlevel 1 goto :download_error

echo.
echo Downloads complete. Install manually in this order:
echo   1. SPIN 4.4 - local drive
echo   2. PEARL 5.5.5
echo   3. SWASH 5.3 - normally C:\SWASH
echo   4. MACRO 5.5.4a - normally below C:\SWASH
echo   5. TOXSWA 5.5.3 - normally C:\SWASH\TOXSWA
echo.
echo Read FOCUS_INSTALLATION_GUIDE.md before running a regulatory model.
start "" "%DL%"
pause
exit /b 0

:download_error
echo.
echo Download failed. The JRC server may block automated downloads.
echo Open FOCUS_INSTALLATION_GUIDE.md and use the official model pages.
pause
exit /b 1
