@echo off
setlocal
cd /d "%~dp0"
echo This is OPTIONAL. Normal EnviroChem startup does not require native Python RDKit.
echo Do not use this to bypass an organisation or Windows Application Control policy.
echo.
if not exist ".venv\Scripts\python.exe" (
  echo Run START_ENVIROCHEM.bat once first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install --prefer-binary -r requirements-envirodesign-native.txt
echo.
echo Installation complete. Native loading can still be blocked by Windows policy.
pause
