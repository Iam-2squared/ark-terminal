@echo off
setlocal
rem Ark Terminal No.1.1 READ ONLY launcher. No broker order permission changes.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-ArkTerminalNo11.ps1" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo ARK_ONE_CLICK_STARTUP_BLOCKED. See the error code above.
  pause
)
exit /b %RC%
