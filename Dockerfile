FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000

WORKDIR /app

COPY requirements.txt ./

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libpq-dev \
    && python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --default-timeout=100 --retries=5 -r requirements.txt \
    && rm -rf /var/lib/apt/lists/*

COPY . .

EXPOSE 8000 3000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn reserva_baep.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120"]
