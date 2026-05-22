FROM python:3.11

WORKDIR /app

COPY . /app

# Instalação com timeout alto e retentativas para evitar falhas em conexões instáveis
RUN pip install --default-timeout=100 --retries=5 -r requirements.txt

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "reserva_baep.wsgi:application"]
