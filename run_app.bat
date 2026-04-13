@echo off
echo Executando migracoes do banco de dados...
.\python_env\tools\python.exe manage.py migrate

echo.
echo Iniciando servidor web do Django...
echo Pressione Ctrl+C para parar o servidor.
.\python_env\tools\python.exe manage.py runserver 0.0.0.0:8000

pause
