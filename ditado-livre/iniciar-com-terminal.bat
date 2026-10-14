@echo off
rem Igual ao iniciar.bat, mas mostra as mensagens (útil para descobrir problemas).
cd /d "%~dp0"
".venv\Scripts\python.exe" -m ditado_livre
pause
