@echo off
chcp 65001 >nul 2>&1
title Hermers - Install
cd /d "%~dp0"
set "EC=0"

call "%~dp0scripts\env.bat"
if errorlevel 1 (
  set "EC=1"
  goto :end
)

echo [Hermers] 安裝套件（editable）...
"%HERMERS_PYTHON%" -m pip install -e .
if errorlevel 1 (
  set "EC=1"
  goto :end
)

echo.
echo [Hermers] 完成。請執行 install-cursor-brain.bat 並設定 CURSOR_API_KEY。
goto :end

:end
if not "%EC%"=="0" echo [Hermers] 安裝失敗（錯誤碼 %EC%）。
call "%~dp0scripts\hold.bat"
exit /b %EC%
