# Local Database Editor – Docker Hub and deployment targets
IMAGE_NAME   := local-database-editor:latest
TARBALL     := local-database-editor.tar.gz
ENV_EXAMPLE := .env copy.example

.PHONY: build build-save deploy-artifacts up down pull push run

# Build the Docker image locally
build:
	docker compose build

# Pull image from Docker Hub (set DOCKER_IMAGE in .env, e.g. username/local-database-editor:latest)
pull:
	docker compose pull

# Run the app (use after pull when using Docker Hub)
up:
	docker compose up -d

# Pull from Docker Hub and run. Usage: make run
run: pull up

# Stop the app
down:
	docker compose down

# Build and push to Docker Hub. Usage: make push DOCKER_USER=your-dockerhub-username
DOCKER_USER ?=
push:
	@test -n "$(DOCKER_USER)" || (echo "Usage: make push DOCKER_USER=your-dockerhub-username" && exit 1)
	docker build -t $(DOCKER_USER)/local-database-editor:latest .
	docker push $(DOCKER_USER)/local-database-editor:latest
	@echo "Pushed $(DOCKER_USER)/local-database-editor:latest"

# Build and save the image as a compressed tarball (air-gapped deployment)
build-save: build
	docker save $(IMAGE_NAME) | gzip > $(TARBALL)
	@echo "Created $(TARBALL)"

# Copy tarball, docker-compose.yml, and env example to DEST (default: ./dist)
# Usage: make deploy-artifacts [DEST=/path/to/deploy]
DEST ?= dist
deploy-artifacts: build-save
	@mkdir -p $(DEST)
	cp $(TARBALL) docker-compose.yml $(ENV_EXAMPLE) $(DEST)/
	@echo "Deploy artifacts copied to $(DEST)/"
