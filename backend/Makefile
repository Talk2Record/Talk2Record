.DEFAULT_GOAL := help

SHELL := /bin/sh

# ---- Docker Compose (local) ----
COMPOSE_LOCAL_FILE ?= docker-compose.local.yml
COMPOSE_LOCAL ?= docker compose -f $(COMPOSE_LOCAL_FILE)

# ---- Docker Compose (docs) ----
COMPOSE_DOCS_FILE ?= docker-compose.docs.yml
COMPOSE_DOCS ?= docker compose -f $(COMPOSE_DOCS_FILE)

# ---- Docker Compose (production) ----
COMPOSE_PROD_FILE ?= docker-compose.production.yml
COMPOSE_PROD ?= docker compose -f $(COMPOSE_PROD_FILE)

# ---- Local build deps (macOS/Homebrew) ----
BREW ?= brew
LIBPQ_PREFIX := $(shell $(BREW) --prefix libpq 2>/dev/null)
LIBPQ_BIN := $(LIBPQ_PREFIX)/bin

.PHONY: help
help:
	@printf "\nTalk2Record backend\n\n"
	@printf "Docker (local):\n"
	@printf "  make build            Build local images\n"
	@printf "  make up               Start local stack (detached)\n"
	@printf "  make down             Stop local stack\n"
	@printf "  make prune            Stop local stack + remove volumes\n"
	@printf "  make logs [S=svc]     Follow logs (optionally one service)\n"
	@printf "  make ps               Show running services\n"
	@printf "  make restart          Restart local stack\n"
	@printf "  make manage ARGS='..' Run manage.py inside container\n"
	@printf "  make bash             Bash inside django container\n"
	@printf "  make django-shell     Django shell inside container\n"
	@printf "  make migrate          Run migrations inside container\n"
	@printf "  make makemigrations   Create migrations inside container\n"
	@printf "  make createsuperuser  Create admin user inside container\n"
	@printf "  make seed ARGS='..'   Run seed data inside container\n"
	@printf "  make collectstatic    Collect static files inside container\n"
	@printf "  make flower           Start Flower (Celery monitor)\n"
	@printf "\nDocs:\n"
	@printf "  make docs             Build/serve docs via Docker\n"
	@printf "  make apidocs          Generate docs sources from docstrings\n"
	@printf "\nPython (uv):\n"
	@printf "  make deps-mac         Install macOS build deps (psycopg)\n"
	@printf "  make uv-sync          Install deps (incl dev)\n"
	@printf "  make venv             Create .venv (uv-managed)\n"
	@printf "  make venv-reset       Recreate .venv from scratch\n"
	@printf "  make run              Run Django locally (no Docker)\n"
	@printf "  make test             Run pytest using the default database\n"
	@printf "  make test-sqlite      Run pytest using a local SQLite database (no Docker/PG)\n"
	@printf "  make coverage         Run coverage + html report\n"
	@printf "  make mypy             Run mypy type checks\n"
	@printf "  make ruff             Run ruff lint\n"
	@printf "  make format           Run ruff format (and fix lint)\n"
	@printf "\nProduction (Docker Compose):\n"
	@printf "  make prod-build       Build production images\n"
	@printf "  make prod-up          Start production stack (detached)\n"
	@printf "  make prod-down        Stop production stack\n\n"

# -----------------------------
# Docker Compose (local)
# -----------------------------

.PHONY: build
build:
	$(COMPOSE_LOCAL) build

.PHONY: up
up:
	$(COMPOSE_LOCAL) up -d --remove-orphans

.PHONY: down
down:
	$(COMPOSE_LOCAL) down

.PHONY: prune
prune:
	$(COMPOSE_LOCAL) down -v

.PHONY: logs
logs:
	@if [ -n "$(S)" ]; then \
		$(COMPOSE_LOCAL) logs -f "$(S)"; \
	else \
		$(COMPOSE_LOCAL) logs -f; \
	fi

.PHONY: ps
ps:
	$(COMPOSE_LOCAL) ps

.PHONY: restart
restart:
	$(COMPOSE_LOCAL) restart

.PHONY: manage
manage:
	@if [ -z "$(ARGS)" ]; then \
		printf "Usage: make manage ARGS='migrate'\n" >&2; \
		exit 2; \
	fi
	$(COMPOSE_LOCAL) run --rm django python ./manage.py $(ARGS)

.PHONY: bash
bash:
	$(COMPOSE_LOCAL) run --rm django bash

.PHONY: django-shell
django-shell:
	$(COMPOSE_LOCAL) run --rm django python ./manage.py shell

.PHONY: migrate
migrate:
	$(COMPOSE_LOCAL) run --rm django python ./manage.py migrate

.PHONY: makemigrations
makemigrations:
	$(COMPOSE_LOCAL) run --rm django python ./manage.py makemigrations

.PHONY: createsuperuser
createsuperuser:
	$(COMPOSE_LOCAL) run --rm django python ./manage.py createsuperuser

.PHONY: seed
seed:
	$(COMPOSE_LOCAL) run --rm django python ./manage.py seed_data $(ARGS)

.PHONY: collectstatic
collectstatic:
	$(COMPOSE_LOCAL) run --rm django python ./manage.py collectstatic --noinput

.PHONY: flower
flower:
	$(COMPOSE_LOCAL) up -d flower

# -----------------------------
# Python (uv)
# -----------------------------

.PHONY: deps-mac
deps-mac:
	@command -v brew >/dev/null 2>&1 || (printf "Homebrew not found. Install from https://brew.sh\n" >&2; exit 1)
	brew install libpq
	@printf "\nIf pg_config still isn't found, add libpq to your PATH:\n"
	@printf "  export PATH=\"%s/bin:$$PATH\"\n\n" "$$(brew --prefix libpq)"

.PHONY: uv-sync
uv-sync:
	@if [ -d ".venv" ] && [ ! -f ".venv/pyvenv.cfg" ]; then \
		printf "Found non-venv .venv directory; recreating it...\n"; \
		rm -rf .venv; \
	fi
	@if [ ! -d ".venv" ]; then \
		uv venv; \
	fi
	@if [ -d "$(LIBPQ_BIN)" ]; then \
		PATH="$(LIBPQ_BIN):$$PATH" uv sync; \
	else \
		uv sync; \
	fi

.PHONY: venv
venv:
	uv venv

.PHONY: venv-reset
venv-reset:
	rm -rf .venv
	uv venv
	uv sync

.PHONY: run
run:
	uv run python manage.py runserver

.PHONY: test
test:
	uv run pytest

.PHONY: test-sqlite
test-sqlite:
	DATABASE_URL=sqlite:////tmp/talk2record-test.sqlite3 uv run pytest

.PHONY: coverage
coverage:
	uv run coverage run -m pytest
	uv run coverage html
	uv run open htmlcov/index.html

.PHONY: mypy
mypy:
	uv run mypy talk2record

.PHONY: ruff
ruff:
	uv run ruff check .

.PHONY: format
format:
	uv run ruff format .
	uv run ruff check . --fix

# -----------------------------
# Docs
# -----------------------------

.PHONY: docs
docs:
	$(COMPOSE_DOCS) up --build

.PHONY: apidocs
apidocs:
	uv run make -C docs apidocs

# -----------------------------
# Docker Compose (production)
# -----------------------------

.PHONY: prod-build
prod-build:
	$(COMPOSE_PROD) build

.PHONY: prod-up
prod-up:
	$(COMPOSE_PROD) up -d --remove-orphans

.PHONY: prod-down
prod-down:
	$(COMPOSE_PROD) down
