@echo off
echo Updating Reachy Mini ElevenLabs app in Control app...
echo.

cd /d "%~dp0"

set VENV_PATH=C:\Users\sammy\AppData\Local\Reachy Mini Control\reachy_mini_elevenlabs_venv
set PYTHON_EXE=%VENV_PATH%\Scripts\python.exe

echo Uninstalling current version from Control app venv...
"%PYTHON_EXE%" -m pip uninstall -y reachy_mini_elevenlabs

echo.
echo Reinstalling with updated metadata...
"%PYTHON_EXE%" -m pip install -e .

echo.
echo Done! Please restart Reachy Mini Control to see the updated icon and description.
echo.
echo The app is installed in editable mode, so code changes are live.
echo Only metadata changes (icon, description) require this reinstall.
echo.
pause
