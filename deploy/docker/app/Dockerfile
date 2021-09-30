# pull official buster slim image
FROM python:3.8-slim-bullseye

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN apt-get update \
  && apt-get install -y --no-install-recommends gcc libpq-dev libxm2-dev libxslt-dev libffi-dev libcairo2-dev libpango1.0-dev

# copy project
COPY . .

# copy entrypoint.sh
COPY ./deploy/docker/app/entrypoint.sh /usr/src/app/
RUN sed -i 's/\r$//g' /usr/src/app/entrypoint.sh \
  && chmod +x /usr/src/app/entrypoint.sh \
  && sed -i 's/psycopg2==/psycopg2-binary==/g' /usr/src/app/requirements/common.txt \
  && pip install -r requirements/dev.txt \
  && sed -i 's/{{ goal }}/docker-dev/g' /usr/src/app/manage.py

# run entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
