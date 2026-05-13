@echo off
chcp 65001 > nul
title SIS LOGÍSTICA 2ºBAEP — Servidor de Produção

echo.
echo ============================================================
echo  SIS LOGÍSTICA 2º BAEP — Sistema Integrado de Controle
echo  Versão 2.2  ^|  Inicializando...
echo ============================================================
echo.

echo [1/4] Verificando ambiente Python...
if not exist ".\python_env\tools\python.exe" (
    echo ERRO: Python portátil não encontrado em .\python_env\tools\python.exe
    pause
    exit /b 1
)

echo [2/4] Aplicando migrações do banco de dados...
.\python_env\tools\python.exe manage.py migrate --run-syncdb
if %errorlevel% neq 0 (
    echo ERRO: Falha nas migrações. Verifique os logs.
    pause
    exit /b 1
)

echo [3/4] Coletando arquivos estáticos...
.\python_env\tools\python.exe manage.py collectstatic --noinput
if %errorlevel% neq 0 (
    echo AVISO: Falha ao coletar estáticos. Continuando...
)

echo [4/4] Iniciando servidor web (0.0.0.0:8000)...
echo.
echo  Acesse: http://10.43.19.224:8000
echo  Ctrl+C para encerrar o servidor.
echo.
.\python_env\tools\python.exe manage.py runserver 0.0.0.0:8000

pause
