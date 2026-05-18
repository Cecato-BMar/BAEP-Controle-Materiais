@echo off
cd /d "%~dp0"
chcp 65001 > nul
title SIS LOGÍSTICA 2ºBAEP — Servidor HTTPS

echo.
echo ============================================================
echo  SIS LOGÍSTICA 2º BAEP — Servidor HTTPS (SSL)
echo  Versão 2.2  |  Porta 8443
echo ============================================================
echo.

echo [1/3] Aplicando migrações do banco de dados...
set "PYTHON_EXE=%~dp0python_env\tools\python.exe"
"%PYTHON_EXE%" manage.py migrate --run-syncdb

echo [2/3] Coletando arquivos estáticos...
"%PYTHON_EXE%" manage.py collectstatic --noinput

echo [3/3] Iniciando servidor HTTPS (0.0.0.0:8443)...
echo.
echo  Acesse: https://10.43.19.224:8443
echo  Ctrl+C para encerrar.
echo.
"%PYTHON_EXE%" manage.py runsslserver 0.0.0.0:8443

pause
