# Local Database Editor

A Django web app that connects to one or more PostgreSQL databases, introspects schemas and tables at runtime, and provides a sortable/filterable data grid with row-level editing. Only changed rows are sent when saving. Authentication is required (single-user).

## Features

- Connect to PostgreSQL databases (e.g. `postgres` at `192.0.0.1:5432`)
- Browse schemas and tables; new tables appear automatically (no code changes)
- Sort and filter on all columns
- Inline row editing; save only modified rows
- Run from **Docker Hub** or ship as a compressed image for air-gapped deployment

### Editing tables

**Only tables that have a primary key can be edited.** The app needs a primary key to identify which row to update when you save. If a table has no primary key, the grid is read-only and shows: *Read-only (table has no primary key)*.


## Prerequisites

- Docker and Docker Compose
- Target PostgreSQL reachable from the host/container (e.g. `192.0.0.1:5432`)

## Quick start (Docker Hub)

1. Copy the example env file and set DB and auth:
   ```bash
   cp ".env copy.example" .env
   # Edit .env: PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD, EDITOR_USERNAME, EDITOR_PASSWORD
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

Transfer the compressed image (and optionally `docker-compose.yml`, `.env copy.example`) to the target:

```bash
scp local-database-editor.tar.gz user@target:/opt/local-database-editor/
# Optional:
scp docker-compose.yml ".env copy.example" user@target:/opt/local-database-editor/
```

### 3. Load the image on the target

On the target machine:

```bash
cd /opt/local-database-editor
gunzip -c local-database-editor.tar.gz | docker load
```

### 4. Configure and run on the target

1. Create `.env` from the example and set at least:
   - `PG_HOST`, `PG_PORT`, `PG_DB`, `PG_USER`, `PG_PASSWORD` (target PostgreSQL)
   - `EDITOR_USERNAME`, `EDITOR_PASSWORD` (login for the editor)
   - `DJANGO_SECRET_KEY` (use a strong random value in production)
   - Leave `DOCKER_IMAGE` unset so Compose uses the loaded image.

2. Start the app (use `--no-build` so Compose uses the loaded image):

   ```bash
   docker compose up -d --no-build
   ```

3. (Optional) Create the single editor user if not already created:
   ```bash
   docker compose exec web python manage.py create_single_user --noinput
   ```

4. Open the app in a browser (e.g. http://localhost:8000 or the host’s IP:8000) and log in.

## Environment variables

| Variable | Description |
|----------|-------------|
| `DOCKER_IMAGE` | Docker image to use (e.g. `username/local-database-editor:latest`). If unset, uses `local-database-editor:latest` (local build). |
| `DJANGO_SECRET_KEY` | Secret key for Django (required in production) |
| `DEBUG` | Set to `0` in production |
| `ALLOWED_HOSTS` | Comma-separated hosts (e.g. `localhost,192.168.1.10`) |
| `PG_HOST`, `PG_PORT`, `PG_DB`, `PG_USER`, `PG_PASSWORD` | Target PostgreSQL connection |
| `EDITOR_USERNAME`, `EDITOR_PASSWORD`, `EDITOR_EMAIL` | Single user created by `create_single_user` |

## Development (without Docker)

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp ".env copy.example" .env
# Set PG_* and EDITOR_* in .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py create_single_user --noinput
.venv/bin/python manage.py runserver
```

Then open http://127.0.0.1:8000 .

## License

This project is licensed under the [MIT License](LICENSE).
