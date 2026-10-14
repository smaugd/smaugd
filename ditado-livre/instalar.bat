@echo off
rem Clique duas vezes aqui para instalar o Ditado Livre.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar.ps1"
pause
