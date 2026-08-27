@echo off
setlocal
set "INSTALLED=%LOCALAPPDATA%\Programs\JARVIS\JARVIS-Debug.exe"
if exist "%INSTALLED%" (
  "%INSTALLED%" --diagnostics %*
) else (
  "%~dp0JARVIS-Debug.exe" --diagnostics %*
)
echo.
pause
