@echo off
echo Installing local Reachy Mini ElevenLabs app to Control app...
echo.

cd /d "%~dp0"

set CONTROL_DIR=C:\Users\sammy\AppData\Local\Reachy Mini Control
set VENV_PATH=%CONTROL_DIR%\reachy_mini_elevenlabs_venv
set UV_EXE=%CONTROL_DIR%\uv.exe

echo Creating virtual environment...
"%UV_EXE%" venv "%VENV_PATH%"

echo.
echo Installing app in editable mode...
"%VENV_PATH%\Scripts\python.exe" -m pip install -e .

echo.
echo Creating metadata file...
set METADATA_FILE=%CONTROL_DIR%\.app_metadata\reachy_mini_elevenlabs.json

if not exist "%CONTROL_DIR%\.app_metadata" mkdir "%CONTROL_DIR%\.app_metadata"

powershell -Command "$metadata = @{subdomain='local-reachy-mini-elevenlabs';id='local/reachy_mini_elevenlabs';sdk='static';cardData=@{short_description='ElevenLabs Conversational AI Agents for Reachy Mini';title='ElevenLabs Conversation';emoji=[char]0x23F8+[char]0xFE0F;colorFrom='blue';sdk='static';colorTo='purple';tags=@('reachy_mini','reachy_mini_python_app','elevenlabs','conversational-ai');pinned=$false};private=$false;tags=@('static','reachy_mini','reachy_mini_python_app','elevenlabs');author='local';local_install=$true;custom_url='http://localhost:7861';venv_path='reachy_mini_elevenlabs_venv'}; $metadata | ConvertTo-Json -Depth 10 | Out-File -FilePath '%METADATA_FILE%' -Encoding UTF8"

echo.
echo Done! The local version is now installed.
echo Refresh the Reachy Mini Control app to see it in the Applications list.
echo.
pause
