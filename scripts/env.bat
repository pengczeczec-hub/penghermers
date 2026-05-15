@echo off
chcp 65001 >nul 2>&1
REM Hermers 共用：切到專案根目錄並設定 HERMERS_ROOT、HERMERS_PYTHON
set "HERMERS_ROOT=%~dp0.."
cd /d "%HERMERS_ROOT%" || exit /b 1
set "HERMERS_ROOT=%CD%"

set "HERMERS_PYTHON="
python -c "import sys" >nul 2>&1
if not errorlevel 1 (
  set "HERMERS_PYTHON=python"
  goto :found
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
  set "HERMERS_PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  goto :found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
  set "HERMERS_PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
  goto :found
)

echo [Hermers] 找不到 Python。請安裝 Python 3.12+ 並重新開啟終端機。
exit /b 1

:found
exit /b 0
