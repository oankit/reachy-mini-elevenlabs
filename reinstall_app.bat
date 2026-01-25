@echo off
REM Reinstall the ElevenLabs app to update Control App metadata
echo ========================================
echo Reinstalling Reachy Mini ElevenLabs App
echo ========================================
echo.
echo This will reinstall the app so the Reachy Control App
echo can detect the settings UI and show the "Open" button.
echo.

REM Uninstall first
echo Uninstalling current version...
pip uninstall -y reachy_mini_elevenlabs

REM Reinstall from current directory
echo.
echo Reinstalling from current directory...
pip install -e .

echo.
echo ========================================
echo Reinstallation complete!
echo ========================================
echo.
echo Please restart the Reachy Control App to see the "Open" button.
echo The settings UI will be available at: http://localhost:7861/
echo.
pause
