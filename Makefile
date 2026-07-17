PYTHON ?= python3
VENV ?= .venv
RUST_REMAP_ENV = CARGO_ENCODED_RUSTFLAGS=$$(printf '%s\037%s' '--remap-path-prefix=$(CURDIR)=.' '--remap-path-prefix='$$HOME'=~')

.PHONY: setup lint format test docs frontend-install frontend-lint frontend-typecheck frontend-test frontend-build frontend-e2e quality desktop-check desktop-build backend-sidecar sidecar-check version-check release-audit release-manifest bundle-check release-check release-build rc-build clean-install-test upgrade-test recovery-test provider-test data-import-test data-certification-test

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
	cd frontend/src-tauri && $(RUST_REMAP_ENV) cargo fmt --check
	cd frontend/src-tauri && $(RUST_REMAP_ENV) cargo clippy --all-targets --all-features -- -D warnings
	cd frontend/src-tauri && $(RUST_REMAP_ENV) cargo test
	cd frontend/src-tauri && $(RUST_REMAP_ENV) cargo check

desktop-build: backend-sidecar
	cd frontend && $(RUST_REMAP_ENV) npm exec tauri build -- --no-bundle

backend-sidecar:
	. $(VENV)/bin/activate && python -m scripts.build_sidecar

sidecar-check: backend-sidecar
	frontend/src-tauri/binaries/orp-backend-$$(rustc -vV | sed -n 's/^host: //p') --version

version-check:
	. $(VENV)/bin/activate && python -m scripts.release_tool version-check

release-audit: version-check
	. $(VENV)/bin/activate && python -m scripts.release_tool release-audit

release-manifest:
	. $(VENV)/bin/activate && python -m scripts.release_tool manifest --profile development

bundle-check:
	. $(VENV)/bin/activate && python -m scripts.release_tool bundle-check

release-check: release-audit
	. $(VENV)/bin/activate && python -m scripts.release_tool release-check --profile development

release-build: quality backend-sidecar
	cd frontend && $(RUST_REMAP_ENV) npm exec tauri build -- --bundles app
	. $(VENV)/bin/activate && python -m scripts.release_tool manifest --profile development
	. $(VENV)/bin/activate && python -m scripts.release_tool bundle-check
	. $(VENV)/bin/activate && python -m scripts.package_smoke

rc-build:
	. $(VENV)/bin/activate && python -m scripts.release_tool policy --profile release-candidate
	$(MAKE) release-build

clean-install-test: release-build
	. $(VENV)/bin/activate && python -m scripts.clean_install_test

upgrade-test: backend-sidecar
	. $(VENV)/bin/activate && python -m scripts.upgrade_test

recovery-test:
	. $(VENV)/bin/activate && python -m scripts.recovery_test

provider-test:
	. $(VENV)/bin/activate && pytest backend/tests/test_provider_validation.py

data-import-test:
	. $(VENV)/bin/activate && pytest backend/tests/test_sprint10_local_integration.py backend/tests/test_provider_validation.py

data-certification-test:
	. $(VENV)/bin/activate && pytest backend/tests/test_provider_fixture_closure.py backend/tests/test_provider_validation.py

quality: lint test frontend-lint frontend-typecheck frontend-test frontend-build desktop-check
	git diff --check
