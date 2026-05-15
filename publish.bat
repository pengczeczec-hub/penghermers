@echo off
chcp 65001 >nul 2>&1
title Hermers - Publish
cd /d "%~dp0"
set "EC=0"

call "%~dp0scripts\env.bat"
if errorlevel 1 (
  set "EC=1"
  goto :end
)

if "%~1"=="" (
  set "MSG=chore: publish site"
) else (
  set "MSG=%*"
)

echo [Hermers] 提交並推送到遠端...
"%HERMERS_PYTHON%" "%HERMERS_ROOT%\tools\git_publish.py" -m "%MSG%"
if errorlevel 1 set "EC=1"

:end
if "%EC%"=="0" (
  echo.
  echo [Hermers] 完成。
) else (
  echo [Hermers] 推送失敗。請確認已 git init、設定 remote，且認證可用。
)
call "%~dp0scripts\hold.bat"
exit /b %EC%
