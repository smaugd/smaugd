@echo off
rem Abre o Ditado Livre sem janela de terminal. Rode instalar.ps1 antes da primeira vez.
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Rode primeiro o instalar.ps1
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" -m ditado_livre
