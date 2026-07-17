PYTHON ?= python3
VENV ?= .venv

.PHONY: setup lint format test docs frontend-install frontend-lint frontend-typecheck frontend-test frontend-build frontend-e2e quality desktop-check desktop-build backend-sidecar sidecar-check

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

frontend-e2e:
	cd frontend && npm run test:e2e

desktop-check:
	cd frontend/src-tauri && cargo fmt --check
	cd frontend/src-tauri && cargo clippy --all-targets --all-features -- -D warnings
	cd frontend/src-tauri && cargo test
	cd frontend/src-tauri && cargo check

desktop-build: backend-sidecar
	cd frontend && npm exec tauri build -- --no-bundle

backend-sidecar:
	. $(VENV)/bin/activate && python scripts/build_sidecar.py

sidecar-check: backend-sidecar
	frontend/src-tauri/binaries/orp-backend-$$(rustc -vV | sed -n 's/^host: //p') --version

quality: lint test frontend-lint frontend-typecheck frontend-test frontend-build desktop-check
	git diff --check
