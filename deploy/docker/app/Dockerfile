# pull official buster slim image
FROM python:3.8-slim-bullseye

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# copy project
COPY . .
# copy entrypoint.sh
COPY ./deploy/docker/app/entrypoint.sh /usr/local/bin/

# install dependencies
RUN BUILD_DEPS=" \
  libxml2-dev \
  libxslt-dev \
  libffi-dev \
  libcairo2-dev \
  libpango1.0-dev \
  gettext \
  locales" \
  && apt-get update && apt-get install -y --no-install-recommends $BUILD_DEPS; \
  sed -i 's/psycopg2==/psycopg2-binary==/g' /usr/src/app/requirements/common.txt; \
  pip install --no-cache-dir -r requirements/dev.txt; \
  apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
  rm -rf '/var/lib/apt/lists/*';\
  sed -i 's/{{ goal }}/docker-dev/g' /usr/src/app/manage.py; \
  sed -i 's/\r$//g' /usr/local/bin/entrypoint.sh; \
  chmod +x /usr/local/bin/entrypoint.sh;

# run entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]
