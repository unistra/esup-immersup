#!/bin/sh
set -e
python manage.py migrate
python manage.py collectstatic --clear --noinput
python manage.py compilemessages || true
exec "$@"
