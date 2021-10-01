#!/bin/sh
set -e

# TODO: uwsgi --socket :8000 --master --enable-threads --module immersionlyceens.wsgi
exec "$@"
