FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive
ENV PORT=8000

WORKDIR /app

COPY requirements.txt ./

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl libpq-dev \
    && python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --default-timeout=100 --retries=5 -r requirements.txt \
    && apt-get remove -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN python manage.py makemigrations --noinput && python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput; gunicorn reserva_baep.wsgi:application --bind 0.0.0.0:${PORT} --workers 3 --timeout 120"]
