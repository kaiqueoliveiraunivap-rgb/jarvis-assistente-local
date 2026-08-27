@echo off
setlocal
title Instalacao do J.A.R.V.I.S.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0runtime\install.ps1" %*
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" echo A instalacao terminou com erro %RESULT%.
pause
exit /b %RESULT%
