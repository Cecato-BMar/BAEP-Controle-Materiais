#!/bin/bash
docker run -d --name baep-test \
  -p 9090:8000 \
  -v "$(pwd)":/app \
  baep-local:latest \
  sh -c "python manage.py migrate --noinput && python setup_master.py && gunicorn reserva_baep.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120"
