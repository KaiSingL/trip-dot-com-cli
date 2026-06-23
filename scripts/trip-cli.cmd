@echo off
setlocal
set VENV_PY=%~dp0..\.venv\Scripts\python.exe
if not exist "%VENV_PY%" set VENV_PY=python
"%VENV_PY%" -m trip_cli %*
endlocal
