@echo off
REM One-click menu for personal-agent-config (Windows). Double-click or run.
REM Reset options back up the managed config first and keep auth/history;
REM reset.py prompts for confirmation before deleting anything.
setlocal
cd /d "%~dp0"
:menu
echo.
echo  personal-agent-config
echo  =====================
echo   1. Install all (Claude + Codex)
echo   2. Install Claude only
echo   3. Install Codex only
echo   4. Reset Claude (keep auth/history) + reinstall
echo   5. Reset Codex (keep auth/history) + reinstall
echo   6. Reset all + reinstall
echo   0. Exit
echo.
set "choice="
set /p "choice=Select [0-6]: "
if "%choice%"=="1" ( call :run & goto end )
if "%choice%"=="2" ( call :run -AgentHost claude & goto end )
if "%choice%"=="3" ( call :run -AgentHost codex & goto end )
if "%choice%"=="4" ( call :run -AgentHost claude -Reset & goto end )
if "%choice%"=="5" ( call :run -AgentHost codex -Reset & goto end )
if "%choice%"=="6" ( call :run -Reset & goto end )
if "%choice%"=="0" ( goto end )
echo Invalid choice.
goto menu

:run
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
exit /b

:end
echo.
echo == finished (exit code %ERRORLEVEL%) ==
pause
endlocal
