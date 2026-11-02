@echo off
setlocal
rem Independent Shadow OneClick. DO NOT replace the existing No.1.1 launcher.
rem Orders stay OFF; the underlying controller must pass its original preflight.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-ArkShadowReadOnly.ps1" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo ARK_SHADOW_STARTUP_BLOCKED. Inspect the new local dashboard or error code above.
  pause
)
exit /b %RC%
