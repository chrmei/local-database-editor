# Local Database Editor

A Django web app that connects to one or more PostgreSQL databases, introspects schemas and tables at runtime, and provides a sortable/filterable data grid with row-level editing. Only changed rows are sent when saving. Authentication is required (single-user).

**All configuration is via environment variables.** Copy `.env.example` to `.env`, set every value, and run. There are no hardcoded defaults in code.

## Features

- Connect to PostgreSQL (host, port, db, user, password from `.env`)
- Browse schemas and tables; new tables appear automatically (no code changes)
- Sort and filter on all columns
- Inline row editing; save only modified rows
- Run from **Docker Hub** or ship as a compressed image for air-gapped deployment

### Editing tables

**Only tables that have a primary key can be edited.** The app needs a primary key to identify which row to update when you save. If a table has no primary key, the grid is read-only and shows: *Read-only (table has no primary key)*.


## Prerequisites

- Docker and Docker Compose
- Target PostgreSQL reachable from the host/container

## Quick start (Docker Hub)

1. Copy the example env file and set **all** variables (no defaults in code):
   ```bash
   cp .env.example .env
   # Edit .env: DJANGO_SECRET_KEY, DEBUG, ALLOWED_HOSTS, PG_ALIAS, PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD, EDITOR_USERNAME, EDITOR_PASSWORD, EDITOR_EMAIL
   # For Docker Hub, set: DOCKER_IMAGE=your-dockerhub-username/local-database-editor:latest
   ```

2. Pull and run with Docker Compose:
   ```bash
   docker compose pull
   docker compose up -d
   ```
   Or with Make: `make pull up`

3. Open http://localhost:8000 and log in with `EDITOR_USERNAME` / `EDITOR_PASSWORD`.

### Using the image from Docker Hub

The Compose file uses the image name from the `DOCKER_IMAGE` env var (see `.env`). Set it to your Docker Hub image, e.g.:

```bash
DOCKER_IMAGE=your-dockerhub-username/local-database-editor:latest
```

If `DOCKER_IMAGE` is unset, Compose falls back to `local-database-editor:latest` (for local builds).

## Publishing to Docker Hub (maintainers)

1. Log in to Docker Hub:
   ```bash
   docker login
   ```

2. Build and push the image:
   ```bash
   make push DOCKER_USER=your-dockerhub-username
   ```
   Or manually:
   ```bash
   docker build -t your-dockerhub-username/local-database-editor:latest .
   docker push your-dockerhub-username/local-database-editor:latest
   ```

3. Users can then set `DOCKER_IMAGE=your-dockerhub-username/local-database-editor:latest` in `.env` and run `docker compose pull && docker compose up -d`.

## Deployment: shipping via compressed Docker image (air-gapped)

Use this when the target machine cannot pull images from a registry.

### 1. Build and save the image (on build machine)

From the project root:

```bash
make build-save
```

This builds the Docker image and saves it as `local-database-editor.tar.gz`.

### 2. Copy to the target machine

Transfer the compressed image (and optionally `docker-compose.yml`, `.env.example`) to the target:

```bash
scp local-database-editor.tar.gz user@target:/opt/local-database-editor/
# Optional:
scp docker-compose.yml .env.example user@target:/opt/local-database-editor/
```

### 3. Load the image on the target

On the target machine:

```bash
cd /opt/local-database-editor
gunzip -c local-database-editor.tar.gz | docker load
```

### 4. Configure and run on the target

1. Create `.env` from the example and set **every** variable (all are required; there are no in-code defaults):
   - `DJANGO_SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
   - `PG_ALIAS`, `PG_HOST`, `PG_PORT`, `PG_DB`, `PG_USER`, `PG_PASSWORD` (target PostgreSQL)
   - `EDITOR_USERNAME`, `EDITOR_PASSWORD`, `EDITOR_EMAIL` (login for the editor)
   - Leave `DOCKER_IMAGE` unset so Compose uses the loaded image.

2. Start the app (use `--no-build` so Compose uses the loaded image):

   ```bash
   docker compose up -d --no-build
   ```

3. (Optional) Create the single editor user if not already created:
   ```bash
   docker compose exec web python manage.py create_single_user --noinput
   ```

4. Open the app in a browser (e.g. http://localhost:8000 or the host's IP:8000) and log in.

## Environment variables

All of these must be set in `.env`; the application does not use fallback defaults.

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Secret key for Django (required) |
| `DEBUG` | `0` or `1` (use `0` in production) |
| `ALLOWED_HOSTS` | Comma-separated hosts (e.g. `localhost,127.0.0.1,0.0.0.0`) |
| `ALLOWED_HOSTS_IP_RANGES` | (Optional) Comma-separated CIDR ranges to add to allowed hosts (e.g. `192.168.178.0/24`). Each range is expanded to individual IPs. |
| `PG_ALIAS` | Django DB alias and label in the UI (e.g. `postgres`) |
| `PG_HOST` | PostgreSQL host |
| `PG_PORT` | PostgreSQL port (e.g. `5432`) |
| `PG_DB` | PostgreSQL database name |
| `PG_USER` | PostgreSQL user |
| `PG_PASSWORD` | PostgreSQL password |
| `EDITOR_USERNAME` | Username for the single editor login |
| `EDITOR_PASSWORD` | Password for the single editor login |
| `EDITOR_EMAIL` | Email for the editor user (used by `create_single_user`) |
| `DOCKER_IMAGE` | (Optional) Docker image to use (e.g. `username/local-database-editor:latest`). If unset, Compose uses `local-database-editor:latest` (local build). |

## Development (without Docker)

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# Set every variable in .env (see table above)
.venv/bin/python manage.py migrate
.venv/bin/python manage.py create_single_user --noinput
.venv/bin/python manage.py runserver
```

Then open http://127.0.0.1:8000 .

## License

This project is licensed under the [MIT License](LICENSE).
