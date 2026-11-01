SHELL := /bin/bash
.DEFAULT_GOAL := help
COMPOSE := docker compose
.PHONY: help doctor env config build model model-refresh model-verify up ps health logs down restart test lint benchmark
help:
	@echo 'doctor env config build model model-refresh model-verify up ps health logs down restart test lint benchmark'
doctor:
	@docker version >/dev/null && $(COMPOSE) version && $(COMPOSE) config --quiet && echo 'Docker and Compose: OK'
env:
	@test -e .env || cp .env.example .env
config:
	$(COMPOSE) config --quiet
build:
	$(COMPOSE) build api ui
	$(COMPOSE) --profile setup build model-setup
model:
	$(COMPOSE) --profile setup run --rm --no-deps model-setup
model-refresh:
	$(COMPOSE) --profile setup run --rm --no-deps model-setup python -m scripts.prepare_models --refresh
model-verify:
	$(COMPOSE) --profile setup run --rm --no-deps model-setup python -m scripts.prepare_models --verify-only
up:
	$(COMPOSE) up -d --no-build api ui
ps:
	$(COMPOSE) ps
health:
	$(COMPOSE) exec -T api python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/health/ready").read().decode())'
	$(COMPOSE) exec -T ui wget -qO- http://127.0.0.1:8080/healthz
logs:
	$(COMPOSE) logs --tail=100 -f api ui
down:
	$(COMPOSE) down
restart:
	$(COMPOSE) restart api ui
test:
	PYTHONPATH=backend python -m pytest backend/tests -q
lint:
	ruff check backend/app backend/scripts backend/tests
benchmark:
	python -m backend.scripts.benchmark --url http://127.0.0.1:8001/v1/sentiment
