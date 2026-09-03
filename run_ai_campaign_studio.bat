@echo off
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"
".venv\Scripts\python.exe" -m ai_campaign_studio.presentation_webview --width 1440 --height 900
pause
