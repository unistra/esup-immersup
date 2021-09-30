=================
Immersion lyceens
=================

# Dockerizing immersion app

## Development

Uses the default Django development server.

1. Rename *.env.dev-dist* to *.env.dev*. in deploy/docker/
1. Update the environment variables in the *docker-compose.yml* and *.env.dev* files.
1. Build the images and run the containers:

    ```sh
    $ docker compose up -d --build
    ```

    Reach [http://localhost:8000](http://localhost:8000). The "app" folder is mounted into the container and your code changes apply automatically.
