@echo off
setlocal
pushd "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m unittest discover -s tests -v
) else (
    python -m unittest discover -s tests -v
)
set "JARVIS_TEST_EXIT=%ERRORLEVEL%"
popd
exit /b %JARVIS_TEST_EXIT%

