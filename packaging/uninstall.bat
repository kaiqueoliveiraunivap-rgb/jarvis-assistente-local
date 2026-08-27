@echo off
setlocal
title Desinstalacao do J.A.R.V.I.S.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0runtime\uninstall.ps1" %*
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" echo A desinstalacao terminou com erro %RESULT%.
pause
exit /b %RESULT%
