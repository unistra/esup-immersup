#!/bin/sh
set -e
cd /home/immersup/web
python manage.py migrate
python manage.py collectstatic --clear --noinput
python manage.py compilemessages || true
exec "$@"
