#!/bin/sh

# Encerra o script se algum comando falhar
set -e

echo "==> [1/3] Aplicando migrações do banco de dados..."
python manage.py migrate --noinput

echo "==> [2/3] Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "==> [3/3] Iniciando o servidor Gunicorn..."
exec gunicorn reserva_baep.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
