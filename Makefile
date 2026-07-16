PYTHON ?= python3
VENV ?= .venv

.PHONY: setup lint format test docs frontend-install frontend-lint frontend-typecheck frontend-test frontend-build quality desktop-check

setup:
	$(PYTHON) -m venv $(VENV)
	. $(VENV)/bin/activate && pip install --upgrade pip && pip install -r requirements-dev.txt

lint:
	. $(VENV)/bin/activate && ruff check .
	. $(VENV)/bin/activate && mypy .

format:
	. $(VENV)/bin/activate && ruff format .
	. $(VENV)/bin/activate && black .

test:
	. $(VENV)/bin/activate && pytest

docs:
	@echo "Documentation build placeholder"

frontend-install:
	cd frontend && npm install

frontend-lint:
	cd frontend && npm run lint

frontend-typecheck:
	cd frontend && npm run typecheck

frontend-test:
	cd frontend && npm run test

frontend-build:
	cd frontend && npm run build

desktop-check:
	cd frontend/src-tauri && cargo fmt --check
	cd frontend/src-tauri && cargo check

quality: lint test frontend-lint frontend-typecheck frontend-test frontend-build
	git diff --check
