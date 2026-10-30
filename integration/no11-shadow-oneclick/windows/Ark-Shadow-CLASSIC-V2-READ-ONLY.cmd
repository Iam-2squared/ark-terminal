@echo off
setlocal
rem Frozen No.1.1 Classic UI V2; orders stay OFF. Does not modify old launcher.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-ArkShadowClassicReadOnly-V2.ps1" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
 echo ARK_SHADOW_CLASSIC_V2_BLOCKED. See the stage and safe error code above.
 pause
)
exit /b %RC%
