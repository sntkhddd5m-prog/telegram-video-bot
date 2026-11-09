FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates curl && rm -rf /var/lib/apt/lists/*
RUN groupadd -r botgroup && useradd -r -g botgroup -u 10001 -m -d /home/botuser botuser
WORKDIR /app
COPY requirements .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements
COPY config/ /app/config/
COPY bot/ /app/bot/
RUN mkdir -p /tmp/tg_video_bot && chown -R botuser:botgroup /tmp/tg_video_bot /app
USER botuser
CMD ["python", "-m", "bot.main"]
