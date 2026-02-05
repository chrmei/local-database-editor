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

## Deployment

The application can be deployed in several ways depending on your environment and requirements.

### Quick Start (Docker Hub)

The fastest way to get started is using a pre-built image from Docker Hub.

1. **Copy the example env file and set all variables** (no defaults in code):
   ```bash
   cp .env.example .env
   # Edit .env: DJANGO_SECRET_KEY, DEBUG, ALLOWED_HOSTS, PG_ALIAS, PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD, EDITOR_USERNAME, EDITOR_PASSWORD, EDITOR_EMAIL
   # For Docker Hub, set: DOCKER_IMAGE=your-dockerhub-username/local-database-editor:latest
   ```

2. **Pull and run with Docker Compose**:
   ```bash
   docker compose pull
   docker compose up -d
   ```
   Or with Make: `make pull up`

3. **Access the application**:
   - Open http://localhost:8088 (or your configured host:port)
   - Log in with `EDITOR_USERNAME` / `EDITOR_PASSWORD`

**Note:** The Compose file uses the image name from the `DOCKER_IMAGE` env var (see `.env`). Set it to your Docker Hub image, e.g.:
```bash
DOCKER_IMAGE=your-dockerhub-username/local-database-editor:latest
```

If `DOCKER_IMAGE` is unset, Compose falls back to `local-database-editor:latest` (for local builds).

### Docker Hub

#### For End Users

1. Set `DOCKER_IMAGE` in your `.env` file to the Docker Hub image:
   ```bash
   DOCKER_IMAGE=jaelevy/local-database-editor:latest
   ```

2. Pull and run:
   ```bash
   docker compose pull
   docker compose up -d
   ```

#### For Maintainers (Publishing Images)

1. **Log in to Docker Hub**:
   ```bash
   docker login
   ```

2. **Build, tag, and push the image**:
   ```bash
   # Set your Docker Hub username and version
   VERSION=1.0.1
   DOCKER_USER=your-dockerhub-username
   
   # Build the image
   docker build -t $DOCKER_USER/local-database-editor:$VERSION .
   docker build -t $DOCKER_USER/local-database-editor:latest .
   
   # Push both tags
   docker push $DOCKER_USER/local-database-editor:$VERSION
   docker push $DOCKER_USER/local-database-editor:latest

   # or use make
   make push DOCKER_USER=your-dockerhub-username VERSION=1.0.1
   ```


3. Users can then set `DOCKER_IMAGE=your-dockerhub-username/local-database-editor:latest` in `.env` and run `docker compose pull && docker compose up -d`.


#### 3. Configure and Run

1. **Create `.env`** from the example and set **every** variable (all are required; there are no in-code defaults):
   - `DJANGO_SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
   - `PG_ALIAS`, `PG_HOST`, `PG_PORT`, `PG_DB`, `PG_USER`, `PG_PASSWORD` (target PostgreSQL)
   - `EDITOR_USERNAME`, `EDITOR_PASSWORD`, `EDITOR_EMAIL` (login for the editor)
   - Leave `DOCKER_IMAGE` unset so Compose uses the loaded image.

2. **Start the app** (use `--no-build` so Compose uses the loaded image):
   ```bash
   docker compose up -d --no-build
   ```

3. **Verify the application**:
   - Open http://localhost:8088 (or the host's IP:8088) and log in
   - The single editor user is created automatically on first run

### Remote Systems (TrueNAS, etc.)

When deploying on TrueNAS or other remote systems, SQLite requires write access to the **directory** containing the database file (not just the file itself) to create lock files.

#### 1. Configure docker-compose.yml

```yaml
services:
  web:
    image: username/local-database-editor:latest
    command: /app/start.sh
    env_file:
      - /mnt/data/apps/local-database-editor/.env
    environment:
      - DJANGO_SETTINGS_MODULE=local_database_editor.settings
      - SQLITE_DB_PATH=/app/data/db.sqlite3
    ports:
      - '8088:8088'
    volumes:
      # Mount the directory, not just the file - SQLite needs write access to create lock files
      - /mnt/data/apps/local-database-editor:/app/data
```

#### 2. Set Proper Permissions

On the remote machine, ensure the directory has write permissions:

```bash
sudo chmod 755 /mnt/data/apps/local-database-editor
sudo chown -R $USER:$USER /mnt/data/apps/local-database-editor
```

#### 3. Update the Image

When a new version is available:

```bash
# Pull the latest image
docker compose pull

# Restart the service
docker compose up -d
```

Or if using TrueNAS UI:
1. Go to your app's settings
2. Click "Update" or "Pull Image"
3. Restart the container

### Production Considerations

- **Set `DEBUG=0`** in your `.env` file for production
- **Use a strong `DJANGO_SECRET_KEY`** - generate one with: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- **Configure `ALLOWED_HOSTS`** with your domain/IP addresses
- **Use HTTPS** in production (configure a reverse proxy like nginx or Traefik)
- **Backup your SQLite database** regularly (located at `/app/data/db.sqlite3` by default)
- **Monitor logs** with `docker compose logs -f` or `make logs`

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
| `SQLITE_DB_PATH` | (Optional) Path to SQLite database file. Defaults to `/app/db.sqlite3`. For remote deployments, set this to a path within a mounted volume (e.g. `/app/data/db.sqlite3`). |

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
