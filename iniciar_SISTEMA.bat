@echo off
cd /d "%~dp0"
title SIS LOGISTICA 2 BAEP - INICIAR

echo.
echo ============================================================
echo  SIS LOGISTICA 2 BAEP - Sistema Integrado de Controle
echo  Versao 2.2 - Inicializacao Segura
echo ============================================================
echo.

set "PYTHON_EXE=%~dp0python_env\tools\python.exe"

echo [1/3] Verificando Ambiente Python...
if not exist "%PYTHON_EXE%" (
    echo AVISO: Ambiente nao encontrado. Tentando restaurar...
    if exist "%~dp0python\python.zip" (
        echo Extraindo python.zip...
        powershell -Command "Expand-Archive -Path '%~dp0python\python.zip' -DestinationPath '%~dp0python_env' -Force"
    )
)

if not exist "%PYTHON_EXE%" (
    echo.
    echo ERRO CRITICO: Python nao encontrado em:
    echo "%PYTHON_EXE%"
    pause
    exit /b 1
)

echo [2/3] Sincronizando Banco de Dados...
"%PYTHON_EXE%" manage.py migrate --run-syncdb

echo [3/3] Iniciando Servidor...
echo.
echo Acesse: http://10.43.19.224:8000
echo.

"%PYTHON_EXE%" manage.py runserver 0.0.0.0:8000

pause
