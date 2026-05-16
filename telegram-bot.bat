@echo off
chcp 65001 >nul 2>&1
title Hermers - Telegram Bot
cd /d "%~dp0"

call "%~dp0scripts\env.bat"
if errorlevel 1 (
  echo [Hermers] Environment error.
  pause
  exit /b 1
)

echo [Hermers] Telegram Bot starting...
echo Send "help" to your bot for commands.
echo Close this window to stop the bot.
echo.

"%HERMERS_PYTHON%" -m hermers.telegram_bot
pause
exit /b %ERRORLEVEL%
