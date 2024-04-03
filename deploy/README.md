========
Immersup
========

# Dockerizing immersup app

## Development

Uses the default Django development server.

1. Rename *.env.dev-dist* to *.env.dev*. in deploy/docker/
1. Update the environment variables in the *docker-compose.yml* and *.env.dev* files.
1. Build the images and run the containers:

    ```sh
    docker compose up -d --build
    ```

    Reach [http://localhost:8000](http://localhost:8000). The "app" folder is mounted into the container and your code changes apply automatically.

    A command could be executed using :

    ```sh
    docker compose exec web python manage.py diffsettings --all
    ```

### Demo edition

Uses django/uwsgi/nginx.

1. Rename *.env.demo-dist to *.env.demo
1. If needed update the environment variables in the *docker-compose.demo.yml* and *.env.demo* files.
1. Build the images and run the containers:

    ```sh
    docker compose -f docker-compose.demo.yml up -d --build
    ```

    Reach [http://localhost](http://localhost).
