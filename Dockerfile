FROM python:3.12-slim-bookworm

# Настройка окружения Python
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app

# Установка системных зависимостей (ffmpeg нужен для работы с видео)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание безопасного пользователя для запуска бота
RUN groupadd -r botgroup && useradd -r -g botgroup -u 10001 -m -d /home/botuser botuser

WORKDIR /app

# Копирование зависимостей и установка библиотек
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование всех файлов проекта из корня репозитория
COPY . /app/

# Создание временной папки для видео и настройка прав
RUN mkdir -p /tmp/tg_video_bot && chown -R botuser:botgroup /tmp/tg_video_bot /app

# Переключение на созданного пользователя
USER botuser

# Команда для запуска бота (укажи имя своего главного файла, например main.py)
CMD ["python", "main.py"]