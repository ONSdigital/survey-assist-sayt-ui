SHELL := /bin/bash

.DEFAULT_GOAL := help

PY ?= python
PKG ?= survey_assist_sayt_ui
IMAGE_NAME ?= survey-assist-sayt-ui
CRED_FILE ?= $(HOME)/gcp-project-creds-ui.json
VERSION ?= $(shell poetry version -s 2>/dev/null || echo 0.0.0+unknown)
GIT_SHA ?= $(shell git rev-parse --short=7 HEAD 2>/dev/null || echo unknown)
BUILD_DATE ?= $(shell date -u '+%Y-%m-%dT%H:%M:%SZ')

CONTAINER_BUILD_ARGS = \
	--build-arg VERSION=$(VERSION) \
	--build-arg GIT_SHA=$(GIT_SHA) \
	--build-arg BUILD_DATE=$(BUILD_DATE)

.PHONY: help all clean install templates run run-docs all-tests test lint format \
	check-python check-python-nofix \
	docker-build docker-run podman-build podman-run \
	manage-users pre-commit-install pre-commit-run pre-push-run \
	secrets-baseline show-build-metadata

help: ## Show the available make targets.
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "%-30s %s\n", $$1, $$2}'

all: help

all: ## Show the available make targets.
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@fgrep "##" Makefile | fgrep -v fgrep

clean: ## Clean the temporary files.
	rm -rf .mypy_cache
	rm -rf .ruff_cache

install:  ## Install main and dev dependencies no root package
	poetry install --no-root

templates:  ## Fetch ONS design system templates.
	poetry run python scripts/fetch_ons_templates.py

## Build the remote-autosuggest.bundle.js file.
## Only required when changing the remote-autosuggest.js file.
build-remote-autosuggest:
	npm run build:js

run:  ## Run the Flask application.
	FLASK_APP=$(PKG).app:create_app poetry run flask --debug run

run-docs: ## Run the mkdocs
	poetry run mkdocs serve

all-tests: ## Run all tests with coverage and fail if coverage is below threshold
	poetry run pytest --ignore=cicd --cov --cov-report=term-missing --cov-fail-under=80

check-python: ## Format and lint the python code (auto fix)
	poetry run ruff check . --fix
	poetry run ruff format .
	poetry run mypy --follow-untyped-imports src/survey_assist_sayt_ui
	poetry run pylint --verbose .
	poetry run bandit -r src/survey_assist_sayt_ui

check-python-nofix: ## Format and lint the python code (no fix)
	poetry run ruff check .
	poetry run ruff format --check .
	poetry run mypy --follow-untyped-imports src/survey_assist_sayt_ui
	poetry run pylint --verbose .
	poetry run bandit -r src/survey_assist_sayt_ui

docker-build:  ## Build the Docker image.
	docker build $(CONTAINER_BUILD_ARGS) -t $(IMAGE_NAME) .

docker-run:  ## Run the Docker container.
	docker run \
		--rm \
		-p 8000:8000 \
		-v $(PWD)/users.json:/app/users.json:ro \
		--mount type=bind,src=$(CRED_FILE),target=/run/secrets/gcp-key.json,readonly \
		-e GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/gcp-key.json \
		--env-file .env \
		$(IMAGE_NAME)

podman-build:  ## Build the Podman image.
	podman build $(CONTAINER_BUILD_ARGS) -t $(IMAGE_NAME) .

podman-run:  ## Run the Podman container.
	podman run \
		--rm \
		-p 8000:8000 \
		-v $(PWD)/users.json:/app/users.json:ro \
		--mount type=bind,src=$(CRED_FILE),target=/run/secrets/gcp-key.json,readonly \
		-e GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/gcp-key.json \
		--env-file .env \
		$(IMAGE_NAME)

manage-users:  ## Show user management commands
	poetry run python scripts/provision_users.py --help

pre-commit-install:  ## Install pre-commit hooks.
	poetry run pre-commit install
	poetry run pre-commit install --hook-type pre-push

pre-commit-run:  ## Run pre-commit hooks on all files.
	poetry run pre-commit run --all-files

pre-push-run:  ## Run pre-commit hooks for the pre-push stage on all files.
	poetry run pre-commit run --hook-stage pre-push --all-files

secrets-baseline:  ## Create a baseline for detect-secrets and audit it.
	poetry run detect-secrets scan > .secrets.baseline
	poetry run detect-secrets audit .secrets.baseline

show-build-metadata:  ## Show metadata that will be included in the image.
	@echo VERSION=$(VERSION)
	@echo GIT_SHA=$(GIT_SHA)
	@echo BUILD_DATE=$(BUILD_DATE)
