# Не знаю нахуя тут питон слим, мне было лень билдить на альпин линукс потому что - долго
# Но никто не мешает билдить на альпине, я пробовал, работает.

FROM python:3.12-slim

WORKDIR /app

# Установка зависимостей через apt-get
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    python3-dev \
    bash \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Указываем путь к ffmpeg
ENV IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg

# Установка Python зависимостей
COPY requirements.txt .
COPY shit.py .
COPY config.py .
COPY README.md .
COPY README.ru.md .

RUN pip install --no-cache-dir -r requirements.txt

# Запуск приложения
CMD ["python", "shit.py"]
