@echo off
chcp 65001 >nul 2>&1
title Hermers - Brain
cd /d "%~dp0"

call "%~dp0scripts\env.bat"
if errorlevel 1 (
  set "EC=1"
  goto :end
)

"%HERMERS_PYTHON%" -m hermers.brain %*
set "EC=%ERRORLEVEL%"

:end
if not "%EC%"=="0" echo [Hermers] 執行失敗（錯誤碼 %EC%）。
call "%~dp0scripts\hold.bat"
exit /b %EC%
