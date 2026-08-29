FROM python:3.12-slim

# Dependências de sistema necessárias
# libpq-dev: cliente PostgreSQL
# libffi-dev, libssl-dev: para criptografia e certificados digitais ICP-Brasil
# curl: healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# Atualiza o pip do base image (corrige PYSEC-2026-* do pip) antes de instalar deps
RUN pip install --no-cache-dir --upgrade "pip>=26.2.1" \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
