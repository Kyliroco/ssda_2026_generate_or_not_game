# Generate or Not - Minimal MVP

This repository contains a minimal Docker MVP:

- A web page served by a small Python web app.
- A PostgreSQL SQL database that starts empty (no game tables, no seed data).
- A Docker Compose v2 stack that runs everything together.

## Architecture

- `web` service:
  - Exposed on host port `6767`.
  - Serves the landing page at `/`.
  - Exposes a basic health endpoint at `/health`.
- `db` service:
  - PostgreSQL 16.
  - Uses a persistent Docker volume.
  - Not exposed to the host (no published DB port).
  - Reachable only by the app through the internal Compose network.

## Requirements

- Docker Engine with Docker Compose v2 support.

## Quick Start

1. Pull and start the stack:

   ```bash
    docker compose pull web db
    docker compose up -d
   ```

2. Open the web page:
   - `http://localhost:6767/`

3. Check health:

   ```bash
   curl http://localhost:6767/health
   ```

## Verify The Database Is Internal-Only

Run:

```bash
docker compose ps
```

Expected result:

- `web` shows `0.0.0.0:6767->6767/tcp` (or equivalent).
- `db` shows no published host port.

## Stop Or Reset

- Stop containers (keep database data):

  ```bash
  docker compose down
  ```

- Stop and remove database data volume:

  ```bash
  docker compose down -v
  ```

## Easy-To-Modify Settings

Values are hardcoded in `docker-compose.yml` for simplicity.

To change runtime settings, edit `docker-compose.yml` directly:

- Web image: `kyliroco/ssda2026:latest`
- Web published port: `6767:6767`
- Database name: `generate_or_not`
- Database user: `game_user`
- Database password: `change_me_now`

## Image Dataset Layout (/data/data)

The app reads images from `/data/data` inside the container.

With the current compose file, host `./data` is mounted to container `/data`,
so image files must be available under `/data/data`.

Expected folders:

- `/data/data/1` for category 1 (AI/synthetic)
- `/data/data/2` for category 2 (human/real)

Important behavior:

- The scan is recursive in both category folders.
- A category 1 image is only eligible when a file with the same filename exists somewhere under `/data/data/2`.
- Category 2 images are eligible when they are valid image files.

Supported image extensions:

- `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`, `.tiff`

Example layout:

```text
/data
  /data
    /1
      /a01
        a01-000u-00-01.png
    /2
      a01-000u-00-01.png
      p01-147-01-03.png
```

In this example, `/data/data/1/a01/a01-000u-00-01.png` can be selected because `a01-000u-00-01.png` exists in `/data/data/2`.

## HTTPS Note

This MVP serves HTTP on port `6767` inside the stack.
For HTTPS, use your existing reverse proxy to terminate TLS and forward traffic to this app on port `6767`.

## GitHub Runner CI

The repository includes a GitHub Actions workflow at `.github/workflows/ci-cd.yml`.

For every push and pull request, GitHub runners will:

- Build the web Docker image.
- Start a temporary PostgreSQL test container.
- Run a container from that image.
- Check `/` and `/health`.

This allows you to rely on runner-based checks instead of local testing.

## Docker Hub Auto Publish

The same workflow publishes the web image to Docker Hub when code is pushed to `main` or `master`.

Required repository secrets:

- `DOCKERUSER`
- `DOCKERPASS`

Default Docker image name:

- `kyliroco/ssda2026`

Set `DOCKERUSER=kyliroco` in GitHub secrets for Docker Hub login.

To change the image name later, edit `DOCKER_IMAGE` in `.github/workflows/ci-cd.yml`.
