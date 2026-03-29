@echo off
setlocal enabledelayedexpansion

REM Ensure script runs from its own folder
cd /d "%~dp0"

REM Activate virtual environment
if exist ".env\Scripts\activate.bat" (
  call ".env\Scripts\activate.bat"
) else (
  echo **Error**: Virtual environment not found at .env\Scripts\activate.bat
  pause
  exit /b 1
)

REM Run PyInstaller with the requested options
pyinstaller "visual_driver.py" --noconsole --collect-all mediapipe --distpath "compile\dist" --specpath "compile\spec" --workpath "compile\build"

REM Attempt to deactivate virtual environment if available
if defined VIRTUAL_ENV (
  if exist "%VIRTUAL_ENV%\Scripts\deactivate.bat" call "%VIRTUAL_ENV%\Scripts\deactivate.bat"
)

echo **Build finished**
pause
