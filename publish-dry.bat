@echo off
chcp 65001 >nul 2>&1
title Hermers - Publish dry-run
cd /d "%~dp0"
set "EC=0"

call "%~dp0scripts\env.bat"
if errorlevel 1 (
  set "EC=1"
  goto :end
)

echo [Hermers] Git 推送預覽（dry-run）...
"%HERMERS_PYTHON%" "%HERMERS_ROOT%\tools\git_publish.py" --dry-run
if errorlevel 1 set "EC=1"

:end
if not "%EC%"=="0" echo [Hermers] 預覽失敗（錯誤碼 %EC%）。
call "%~dp0scripts\hold.bat"
exit /b %EC%
