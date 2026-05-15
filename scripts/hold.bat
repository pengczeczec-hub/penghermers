@echo off
REM 雙擊 .bat 時保留視窗；終端機可設 HERMERS_NO_PAUSE=1
if defined HERMERS_NO_PAUSE exit /b 0
echo.
pause
exit /b 0
