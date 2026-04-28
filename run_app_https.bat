@echo off
echo Executando migracoes do banco de dados...
.\python_env\tools\python.exe manage.py migrate

echo.
echo Iniciando SERVIDOR SEGURO (HTTPS) do Django...
echo O PWA estara disponivel para instalacao em toda a rede.
echo IMPORTANTE: Ao acessar pela primeira vez, clique em "Avancado" e "Prosseguir" no navegador.
echo.
echo Pressione Ctrl+C para parar o servidor.

.\python_env\tools\python.exe manage.py runsslserver 0.0.0.0:8000

pause
