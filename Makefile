# Local Database Editor – Docker Hub and deployment targets
IMAGE_NAME   := local-database-editor:latest
TARBALL     := local-database-editor.tar.gz
ENV_EXAMPLE := .env.example

# Load DOCKER_USER and VERSION from .env file if it exists (ignoring comments and empty lines)
# Users can also override via command line: make push DOCKER_USER=user VERSION=1.0.0
DOCKER_USER ?= $(shell grep -E '^DOCKER_USER=' .env 2>/dev/null | cut -d'=' -f2 | head -1)
VERSION ?= $(shell grep -E '^VERSION=' .env 2>/dev/null | cut -d'=' -f2 | head -1)

# Fallback defaults if not found in .env
DOCKER_USER ?= jaelevy
VERSION ?= 1.0.1

# Construct full image name for Docker Hub
FULL_IMAGE_NAME := $(DOCKER_USER)/local-database-editor

.PHONY: build build-save deploy-artifacts up down pull push push-version run logs shell clean help

# Default target
help:
	@echo "Available targets:"
	@echo "  make build          - Build the Docker image locally"
	@echo "  make push           - Build and push version $(VERSION) + latest to Docker Hub"
	@echo "  make push-version   - Build and push only version $(VERSION) (no latest tag)"
	@echo "  make pull           - Pull image from Docker Hub"
	@echo "  make up             - Start the app"
	@echo "  make down           - Stop the app"
	@echo "  make run            - Pull and start the app"
	@echo "  make logs           - Show container logs"
	@echo "  make shell          - Open shell in running container"
	@echo "  make build-save     - Build and save image as compressed tarball"
	@echo "  make deploy-artifacts - Copy deployment artifacts to dist/"
	@echo ""
	@echo "Variables (from .env or override):"
	@echo "  DOCKER_USER=$(DOCKER_USER)"
	@echo "  VERSION=$(VERSION)"

# Build the Docker image locally
build:
	docker compose build

# Pull image from Docker Hub (uses DOCKER_IMAGE from .env)
pull:
	docker compose pull

# Run the app (use after pull when using Docker Hub)
up:
	docker compose up -d

# Pull from Docker Hub and run
run: pull up

# Stop the app
down:
	docker compose down

# Show container logs
logs:
	docker compose logs -f

# Open shell in running container
shell:
	docker compose exec web /bin/bash

# Build and push version + latest tags to Docker Hub
# Reads DOCKER_USER and VERSION from .env (or use: make push DOCKER_USER=user VERSION=1.0.2)
push:
	@echo "Building and pushing $(FULL_IMAGE_NAME):$(VERSION) and $(FULL_IMAGE_NAME):latest"
	@test -n "$(DOCKER_USER)" || (echo "Error: DOCKER_USER not set. Set it in .env or use: make push DOCKER_USER=username" && exit 1)
	@test -n "$(VERSION)" || (echo "Error: VERSION not set. Set it in .env or use: make push VERSION=1.0.0" && exit 1)
	docker build -t $(FULL_IMAGE_NAME):$(VERSION) -t $(FULL_IMAGE_NAME):latest .
	docker push $(FULL_IMAGE_NAME):$(VERSION)
	docker push $(FULL_IMAGE_NAME):latest
	@echo ""
	@echo "✓ Successfully pushed:"
	@echo "  - $(FULL_IMAGE_NAME):$(VERSION)"
	@echo "  - $(FULL_IMAGE_NAME):latest"

# Build and push only version tag (no latest)
push-version:
	@echo "Building and pushing $(FULL_IMAGE_NAME):$(VERSION)"
	@test -n "$(DOCKER_USER)" || (echo "Error: DOCKER_USER not set. Set it in .env or use: make push-version DOCKER_USER=username" && exit 1)
	@test -n "$(VERSION)" || (echo "Error: VERSION not set. Set it in .env or use: make push-version VERSION=1.0.0" && exit 1)
	docker build -t $(FULL_IMAGE_NAME):$(VERSION) .
	docker push $(FULL_IMAGE_NAME):$(VERSION)
	@echo ""
	@echo "✓ Successfully pushed: $(FULL_IMAGE_NAME):$(VERSION)"

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

# Clean up local build artifacts
clean:
	rm -f $(TARBALL)
	@echo "Cleaned up build artifacts"
