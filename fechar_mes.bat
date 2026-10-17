@echo off
chcp 65001 >nul
title Fechamento mensal - Tarvo
cd /d "%~dp0"

rem Procura um Python que tenha pandas e openpyxl, nesta ordem:
rem   1) .venv do projeto  2) Python instalado no usuario  3) py / python do PATH
set "PY="
if exist ".venv\Scripts\python.exe" call :testar ".venv\Scripts\python.exe"
if not defined PY if exist "C:\Users\%USERNAME%\AppData\Local\Python\bin\python.exe" call :testar "C:\Users\%USERNAME%\AppData\Local\Python\bin\python.exe"
if not defined PY call :testar py
if not defined PY call :testar python

if not defined PY (
  echo.
  echo  ============================================================
  echo   Nao encontrei um Python com as bibliotecas necessarias.
  echo.
  echo   O programa precisa do Python 3.10 ou superior com pandas e
  echo   openpyxl instalados. Peca ajuda a quem mantem o programa,
  echo   ou siga a "Instalacao do zero" no README.md:
  echo       python -m venv .venv
  echo       .venv\Scripts\pip install -r requirements.txt
  echo  ============================================================
  echo.
  pause
  exit /b 1
)

echo.
echo  Abrindo a tela do fechamento no navegador...
echo  Deixe esta janela aberta enquanto usa a tela. Para sair, feche-a.
echo.
%PY% -m app
echo.
echo  O programa foi encerrado.
pause
exit /b 0

:testar
"%~1" -c "import pandas, openpyxl" >nul 2>&1
if not errorlevel 1 set PY="%~1"
exit /b 0
