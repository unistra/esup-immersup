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
COPY ./deploy/docker/app/entrypoint.sh /usr/local/bin

# install dependencies
RUN apt-get update \
  && apt-get install -y --no-install-recommends libxml2-dev libxslt-dev libffi-dev libcairo2-dev libpango1.0-dev \
  && sed -i 's/psycopg2==/psycopg2-binary==/g' /usr/src/app/requirements/common.txt \
  && sed -i 's/{{ goal }}/docker-dev/g' /usr/src/app/manage.py \
  && sed -i 's/\r$//g' /usr/local/bin/entrypoint.sh \
  && chmod +x /usr/local/bin/entrypoint.sh \
  && pip install -r requirements/dev.txt

# run entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]
