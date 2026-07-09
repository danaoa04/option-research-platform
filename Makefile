PYTHON ?= python3
VENV ?= .venv

.PHONY: setup lint format test docs

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
