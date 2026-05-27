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

## HTTPS Note

This MVP serves HTTP on port `6767` inside the stack.
For HTTPS, use your existing reverse proxy to terminate TLS and forward traffic to this app on port `6767`.

## GitHub Runner CI

The repository includes a GitHub Actions workflow at `.github/workflows/ci-cd.yml`.

For every push and pull request, GitHub runners will:

- Validate Docker Compose.
- Pull the web image from Docker Hub.
- Start the stack on the runner.
- Check `/` and `/health`.
- Verify the database is internal-only (no host-published DB port).
- Verify the database starts empty.

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
