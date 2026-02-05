#!/bin/bash
set -e

# Create data directory with proper permissions
mkdir -p /app/data
chmod 777 /app/data

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Create single user if it doesn't exist
echo "Creating single user..."
python manage.py create_single_user --noinput 2>/dev/null || true

# Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:8088 --timeout 120 --workers 2 local_database_editor.wsgi:application
