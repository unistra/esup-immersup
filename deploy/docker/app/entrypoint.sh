#!/bin/sh

# python manage.py flush --no-input
python manage.py migrate
python manage.py compilemessages
# python manage.py collectstatic --noinput

# TODO: uwsgi --socket :8000 --master --enable-threads --module immersionlyceens.wsgi
exec "$@"
