# Developer workflow for fastapi-locale. Every target runs through uv.
#
#   make dev        install the locked environment
#   make lint       ruff check and format check, markdownlint
#   make fmt        apply ruff fixes and formatting
#   make type       mypy --strict
#   make layers     import-linter layering contracts
#   make security   bandit scan
#   make check      lint + type + layers + security
#   make test       unit tests
#   make test-int   integration tests
#   make test-e2e   end-to-end tests (Uvicorn and CLI subprocesses)
#   make test-all   whole suite with coverage
#   make bench      performance budget checks
#   make diagrams   render PlantUML diagrams (needs Docker)
#   make docs       build the documentation site in strict mode
#   make build      build wheel and sdist
#   make clean      remove build and test artifacts

.PHONY: dev lint fmt type layers security check test test-int test-e2e test-all bench \
        diagrams docs build clean

PYTEST    := uv run pytest
COV_FLAGS := --cov --cov-report=term-missing --cov-report=xml:coverage.xml

dev:
	uv sync --locked
	uv run pre-commit install

lint:
	uv run ruff check src tests examples
	uv run ruff format --check src tests examples

fmt:
	uv run ruff check --fix src tests examples
	uv run ruff format src tests examples

type:
	uv run mypy

layers:
	uv run lint-imports

security:
	uv run bandit -c pyproject.toml -r src -ll -ii

check: lint type layers security

test:
	$(PYTEST) -m unit

test-int:
	$(PYTEST) -m integration

test-e2e:
	$(PYTEST) -m e2e

test-all:
	$(PYTEST) $(COV_FLAGS)

bench:
	$(PYTEST) -m benchmark --benchmark-enable --benchmark-only

diagrams:
	scripts/render-diagrams.sh

docs:
	uv run mkdocs build --strict

build:
	uv build

clean:
	rm -rf dist build site htmlcov coverage.xml .coverage .pytest_cache .mypy_cache .ruff_cache \
	       .hypothesis .benchmarks
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
