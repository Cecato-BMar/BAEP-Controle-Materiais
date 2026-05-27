FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000

WORKDIR /app

COPY requirements.txt ./

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --default-timeout=100 --retries=5 -r requirements.txt \
    && apt-get remove -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN chmod +x /app/entrypoint.sh
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
