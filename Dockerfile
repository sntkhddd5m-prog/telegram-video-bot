FROM python:3.12-slim-bookworm

# Настройка окружения Python
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app

# Установка системных зависимостей (ffmpeg нужен для видео)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание безопасного пользователя
RUN groupadd -r botgroup && useradd -r -g botgroup -u 10001 -m -d /home/botuser botuser

WORKDIR /app

# Копирование всех файлов проекта из корня
COPY . /app/

# Универсальная установка зависимостей (поддерживает и requirements.txt, и просто requirements)
RUN pip install --no-cache-dir --upgrade pip && \
    if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; \
    elif [ -f requirements ]; then pip install --no-cache-dir -r requirements; \
    fi

# Создание временной папки и настройка прав
RUN mkdir -p /tmp/tg_video_bot && chown -R botuser:botgroup /tmp/tg_video_bot /app

# Переключение на пользователя
USER botuser

# Команда для запуска бота
CMD ["python", "main.py"]