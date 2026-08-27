@echo off
setlocal EnableExtensions
pushd "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo J.A.R.V.I.S. ainda nao foi instalado. Execute install.bat primeiro.
    popd
    exit /b 1
)

if not exist "logs" mkdir "logs"
".venv\Scripts\python.exe" main.py %*
set "JARVIS_EXIT=%ERRORLEVEL%"
if not "%JARVIS_EXIT%"=="0" (
    echo %date% %time% - Falha de inicializacao, codigo %JARVIS_EXIT%>>"logs\startup_errors.log"
    echo J.A.R.V.I.S. encerrou com erro. Consulte logs\jarvis.log.
)
popd
exit /b %JARVIS_EXIT%

