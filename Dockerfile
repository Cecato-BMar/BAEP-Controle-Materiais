FROM python:3.11

WORKDIR /app

COPY . /app

# Instalação com timeout alto e retentativas para evitar falhas em conexões instáveis
RUN pip install --default-timeout=100 --retries=5 -r requirements.txt

# Torna o entrypoint executável
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

# Usa o entrypoint que aplica migrations antes de iniciar o gunicorn
CMD ["/app/entrypoint.sh"]
