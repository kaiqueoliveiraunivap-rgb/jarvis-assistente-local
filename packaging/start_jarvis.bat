@echo off
setlocal
set "INSTALLED=%LOCALAPPDATA%\Programs\JARVIS\JARVIS.exe"
if exist "%INSTALLED%" (
  start "" "%INSTALLED%" %*
) else (
  start "" "%~dp0JARVIS.exe" %*
)
