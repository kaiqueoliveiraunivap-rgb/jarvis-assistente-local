@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo ERRO: crie a venv e instale as dependencias antes do build.
  exit /b 1
)
".venv\Scripts\python.exe" scripts\build_release.py
exit /b %ERRORLEVEL%
