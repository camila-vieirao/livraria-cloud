FROM python:3.12-slim

# Numero do build do Azure Pipelines; aparece no painel (/info).
ARG BUILD_ID=local
ENV BUILD_ID=${BUILD_ID}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 3000

# 1 worker + threads: o registro de requisicoes do painel fica em memoria.
CMD ["gunicorn", "--workers", "1", "--threads", "4", "-b", "0.0.0.0:3000", "app:create_app()"]
