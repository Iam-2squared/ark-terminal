@echo off
setlocal
rem Original rich Ark UI and existing Frozen Shadow observer. Orders remain OFF.
rem Old No.1.1 shortcut, files, models and workbook data are unchanged.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-ArkShadowClassicReadOnly.ps1" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo ARK_SHADOW_CLASSIC_STARTUP_BLOCKED. See only the safe stage/error code above.
  pause
)
exit /b %RC%
