@echo off
REM One-click installer for personal-agent-config (Windows).
REM Double-click in Explorer, or run from a terminal. No admin needed
REM (install.ps1 does user-scope installs only). Prereqs still apply:
REM git, node, claude, codex, python on PATH + .env with the token filled.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
echo.
echo == install.ps1 finished (exit code %ERRORLEVEL%) ==
pause
