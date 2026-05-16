@echo off
chcp 65001 >nul 2>&1
title Hermes
cd /d "%~dp0"
call "%~dp0scripts\env.bat" || exit /b 1
"%HERMERS_PYTHON%" hermes_main.py %*
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" call "%~dp0scripts\hold.bat"
exit /b %EC%
