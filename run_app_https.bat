@echo off
cd /d "%~dp0"
title SIS LOGISTICA 2 BAEP - Servidor HTTPS

echo.
echo ============================================================
echo  SIS LOGISTICA 2 BAEP - Servidor HTTPS (SSL)
echo  Versao 2.2  ^|  Porta 8443
echo ============================================================
echo.

echo [1/3] Aplicando migracoes do banco de dados...
.\python_env\tools\python.exe manage.py migrate --run-syncdb

echo [2/3] Coletando arquivos estaticos...
.\python_env\tools\python.exe manage.py collectstatic --noinput

echo [3/3] Iniciando servidor HTTPS (0.0.0.0:8443)...
echo.
echo  Acesse: https://10.43.19.224:8443
echo  Ctrl+C para encerrar.
echo.
.\python_env\tools\python.exe manage.py runsslserver 0.0.0.0:8443

pause
