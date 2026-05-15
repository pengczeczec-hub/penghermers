@echo off
chcp 65001 >nul 2>&1
title Hermers - Telegram Bot（請保持此視窗開啟）
cd /d "%~dp0"

call "%~dp0scripts\env.bat"
if errorlevel 1 (
  echo [Hermers] 環境錯誤。
  pause
  exit /b 1
)

echo [Hermers] Telegram Bot 啟動中…
echo 在 Telegram 對 Bot 傳 /help 查看指令。
echo 關閉此視窗即停止 Bot。
echo.

"%HERMERS_PYTHON%" -m hermers.telegram_bot
pause
exit /b %ERRORLEVEL%
