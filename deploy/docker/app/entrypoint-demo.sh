#!/bin/sh
set -e
cd /home/immersup/web
python manage.py migrate
python manage.py collectstatic --clear --noinput
python manage.py compilemessages || true
python manage.py restore_group_rights
python manage.py loaddata higher
python manage.py loaddata dummy_establishment
python manage.py loaddata coursetype
python manage.py loaddata canceltype
python manage.py loaddata evaluationtype
python manage.py loaddata publictype
python manage.py loaddata informationtext
python manage.py loaddata evaluation_form_link
exec "$@"
