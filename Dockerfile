# ==========================================
# Etapa 1: Compilação das dependências
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala bibliotecas necessárias para build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia dependências e instala no escopo do root user
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ==========================================
# Etapa 2: Imagem final para execução
# ==========================================
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH=/root/.local/bin:$PATH

# Instala dependências de runtime necessárias para o PostgreSQL e ReportLab
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copia pacotes instalados da etapa de build
COPY --from=builder /root/.local /root/.local

# Copia os arquivos do projeto
COPY . .

# Permissão de execução para o entrypoint
RUN chmod +x docker-entrypoint.sh

# Porta interna padrão do container
EXPOSE 8000

# Script de entrada para migrações e inicialização
ENTRYPOINT ["/app/docker-entrypoint.sh"]
