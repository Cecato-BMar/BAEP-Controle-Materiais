@echo off
chcp 65001 > nul
title SIS LOGISTICA 2 BAEP - Servidor de Producao

echo.
echo ============================================================
echo  SIS LOGISTICA 2 BAEP - Sistema Integrado de Controle
echo  Versao 2.2  ^|  Inicializando...
echo ============================================================
echo.

echo [1/4] Verificando ambiente Python...
if not exist ".\python_env\tools\python.exe" (
    echo ERRO: Python portatil nao encontrado em .\python_env\tools\python.exe
    pause
    exit /b 1
)

echo [2/4] Aplicando migracoes do banco de dados...
.\python_env\tools\python.exe manage.py migrate --run-syncdb
if %errorlevel% neq 0 (
    echo ERRO: Falha nas migracoes. Verifique os logs.
    pause
    exit /b 1
)

echo [3/4] Coletando arquivos estaticos...
.\python_env\tools\python.exe manage.py collectstatic --noinput
if %errorlevel% neq 0 (
    echo AVISO: Falha ao coletar estaticos. Continuando...
)

echo [4/4] Iniciando servidor web (0.0.0.0:8000)...
echo.
echo  Acesse: http://localhost:8000 ou http://10.43.19.224:8000
echo  Ctrl+C para encerrar o servidor.
echo.
.\python_env\tools\python.exe manage.py runserver 0.0.0.0:8000

pause
