FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Код бэкенда -> /app (чтобы import app.* работал из WORKDIR /app),
# собранный фронтенд -> /app/frontend/dist (совпадает с PROJECT_ROOT/frontend/dist в config.py)
COPY backend /app
COPY frontend/dist /app/frontend/dist

EXPOSE 8000

