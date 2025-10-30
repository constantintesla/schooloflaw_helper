# syntax=docker/dockerfile:1
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

WORKDIR /app

# Системные зависимости (при необходимости можно расширить)
RUN apt-get update && apt-get install -y --no-install-recommends \
		curl ca-certificates \
	&& rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Копируем исходники
COPY src /app/src
COPY templates /app/templates
COPY data /app/data

# Переменные окружения ожидаются через docker-compose или docker run
# BOT_TOKEN, ADMIN_PASSWORD

EXPOSE 8001

CMD ["python", "-m", "src.run_all"]
