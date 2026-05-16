@echo off
chcp 65001 >nul 2>&1
title Hermes - Install Cursor Brain
cd /d "%~dp0\tools\cursor_brain"

where node >nul 2>&1
if errorlevel 1 (
  echo [Hermes] 請先安裝 Node.js 20+：https://nodejs.org/
  pause
  exit /b 1
)

echo [Hermes] 安裝 @cursor/sdk ...
call npm install
if errorlevel 1 (
  echo [Hermes] npm install 失敗
  pause
  exit /b 1
)

echo.
echo [Hermes] 完成。請在 .env 設定 CURSOR_API_KEY
echo 來源：Cursor 儀表板 -^> Integrations -^> User API Keys
echo.
pause
exit /b 0
