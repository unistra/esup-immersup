#!/bin/sh

set -e


echo "Waiting for postgres..."

while !</dev/tcp/db/5432; do sleep 3; done;

echo "PostgreSQL started"

# python manage.py flush --no-input
python manage.py migrate
# python manage.py collectstatic --noinput

# TODO: uwsgi --socket :8000 --master --enable-threads --module immersionlyceens.wsgi
exec "$@"
