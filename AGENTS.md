# Repository Instructions

## Language

- Use English for all repository artifacts: code, documentation, comments, commit messages, and UI text.

## Product Goal

- This project is a game where players decide whether a handwriting sample is real or AI-generated.

## Deployment Constraints

- Target platform: TrueNAS SCALE.
- Orchestration: Docker Compose v2 format.
- Public app entrypoint: port 6767.
- HTTPS termination is expected at the existing reverse proxy, which forwards traffic to this project on port 6767.

## Data Constraints

- Use a SQL database.
- The database must remain internal-only and must not publish a host port.
- Player score data is managed by the application layer.

## Maintainability

- Keep the architecture simple and easy to modify.
- Keep configuration centralized in environment variables.
- Prefer minimal, focused changes over broad refactors.

## Validation Strategy

- Prefer GitHub runner-based validation through workflows.
- Keep local test requirements optional and lightweight.
