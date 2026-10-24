@echo off
setlocal
title Flashcards
cd /d "%~dp0"

rem Double-click this file to start the flashcards with VoiceStudio support.

if not exist "serve.py" goto notextracted
if not exist "index.html" goto notextracted

set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY python3 --version >nul 2>&1 && set "PY=python3"
if not defined PY goto nopython

%PY% serve.py
echo.
echo  Flashcards has stopped. You can close this window.
pause
exit /b

:notextracted
echo.
echo  This file is still inside the ZIP, so it cannot start yet.
echo.
echo  1. Close this window.
echo  2. Right-click the ZIP file you downloaded and choose "Extract All...".
echo  3. Open the new folder and double-click "Start Flashcards" again.
echo.
pause
exit /b

:nopython
echo.
echo  One free program is needed first: Python.
echo.
echo  The Microsoft Store will now open on the Python page.
echo  1. Click "Get" (or "Install") and wait until it has finished.
echo  2. Double-click "Start Flashcards" again.
echo.
echo  If the Store does not open, get Python from:
echo  https://www.python.org/downloads/windows/
echo  (in that installer, tick "Add python.exe to PATH").
echo.
start "" "ms-windows-store://pdp/?productid=9NCVDN91XZQP"
pause
exit /b
