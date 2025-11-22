#!/bin/sh

# Exit immediately if a command fails
set -e

echo "============================"
echo "🚀 Starting Django container"
echo "============================"

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
while ! pg_isready -h "$SQL_HOST" -p "$SQL_PORT" -q -U "$SQL_USER"; do
  echo "PostgreSQL not ready yet, retrying in 2 seconds..."
  sleep 2
done
echo "✅ PostgreSQL is ready!"

# Apply database migrations
echo "🛠️  Applying database migrations..."
python manage.py migrate --noinput
echo "✅ Migrations applied."

# Collect static files
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput --clear
echo "✅ Static files collected."

# Create superuser if env variables are set
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
    echo "👤 Creating superuser (if not exists)..."
    python manage.py create_superuser_if_not_exists \
        --username "$DJANGO_SUPERUSER_USERNAME" \
        --email "$DJANGO_SUPERUSER_EMAIL" \
        --password "$DJANGO_SUPERUSER_PASSWORD"
    echo "✅ Superuser created (or already exists)."
fi

# Start Gunicorn
echo "🚀 Starting Gunicorn server..."
exec gunicorn BLSSPAIN.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
