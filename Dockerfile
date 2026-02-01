FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "local_database_editor.wsgi:application"]
