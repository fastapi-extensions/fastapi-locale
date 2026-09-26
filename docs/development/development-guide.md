# Development guide

| Field | Value |
| --- | --- |
| Document | Development guide |
| Version | 0.1 |
| Status | Draft for review |
| Owner | Kapil Dagur |
| Last updated | 2026-09-26 |

## 1. Set up

### Dev container (recommended)

Open the repository in VS Code and choose "Reopen in Container". The container has Python 3.12, uv,
Node (for markdownlint) and access to the host's Docker (for diagrams). `post-create.sh` installs the
locked environment and the git hooks, then prints the tool versions.

### Without a container

Install [uv](https://docs.astral.sh/uv/) and run:

```sh
make dev    # uv sync --locked, then pre-commit install
```

uv installs the right Python version if it is missing. Docker is only needed for `make diagrams`.

## 2. Everyday commands

| Command | What it runs |
| --- | --- |
| `make fmt` | Ruff fixes and formatting |
| `make check` | Ruff, format check, mypy strict, import-linter layering contracts, bandit |
| `make test` | Unit tests |
| `make test-int` | Integration tests |
| `make test-e2e` | End-to-end tests (Uvicorn and the CLI in subprocesses) |
| `make test-all` | The whole suite with coverage; fails under 95 percent |
| `make bench` | Performance budgets (NFR-01, NFR-02) |
| `make docs` | Documentation site in strict mode |
| `make diagrams` | Render PlantUML sources to SVG with the pinned Docker image |
| `make build` | Wheel and sdist |

The git hooks run Ruff, mypy, import-linter and markdownlint on each commit.

## 3. Repository layout

```text
src/fastapi_locale/     the library; core modules start with an underscore
src/fastapi_locale/locales/   built-in error catalogs (.pot and .po)
tests/unit/             one module at a time
tests/integration/      the library inside FastAPI applications, in process
tests/e2e/              real Uvicorn server and CLI subprocesses
tests/benchmark/        performance budgets
tests/data/locales/     .po files used by tests, compiled per session
examples/basic/         a runnable example application
docs/                   documentation site and engineering documents
docs/diagrams/          PlantUML sources and rendered SVGs
scripts/                maintenance scripts
```

The layering rules in the [detailed design](../design/detailed-design.md) are enforced by import-linter:
core modules never import FastAPI, Starlette or Pydantic.

## 4. Working on the built-in error messages

The English templates are the `TEMPLATES` table in `src/fastapi_locale/_errors_catalog.py`. After
changing it:

```sh
uv run python scripts/sync_error_catalog.py          # rewrite the .pot and merge into every .po
uv run python scripts/sync_error_catalog.py --init ja   # start a new language
```

CI runs the same script with `--check`. A unit test fails when pydantic-core gains an error type that has
no template.

## 5. Diagrams

Diagrams are UML in PlantUML, sources in `docs/diagrams/*.puml`, one shared style in
`docs/diagrams/include/style.iuml`. Run `make diagrams` and commit the `.puml` and `.svg` files together.
CI renders them again and fails if the committed SVGs differ.

## 6. Tests

Follow the [test plan](../testing/test-plan.md). Put a test at the lowest level that can prove the
behaviour. Tests are marked `unit`, `integration`, `e2e` or `benchmark` automatically from their
directory. Warnings are errors, so a deprecation in a dependency shows up at once.

## 7. Continuous integration

| Job | Purpose |
| --- | --- |
| Lint, types, layering, security | Static checks, catalog sync, markdownlint |
| Tests / Python 3.11 to 3.14 | Whole suite with coverage |
| Lowest supported dependencies | Unit and integration tests with the lowest allowed FastAPI, Pydantic and Babel |
| Tests / macOS, Windows | Unit and integration tests |
| Performance budget | Benchmarks |
| Documentation and diagrams | Strict docs build; rendered diagrams match their sources |

CI also runs every Monday to catch breaking upstream releases, and CodeQL and dependency review run on
pull requests.

## 8. Releasing

1. Update `version` in `pyproject.toml` and add a `CHANGELOG.md` section for it.
2. Merge to `main` with CI green.
3. Tag `vX.Y.Z` (or `vX.Y.ZrcN` for a pre-release) and push the tag.

The release workflow checks the tag against `pyproject.toml` and the changelog, runs the tests, builds and
inspects the wheel, publishes with PyPI trusted publishing (TestPyPI for pre-releases) and creates the
GitHub release from the changelog section.

Before the first release, native speakers should review the built-in translations.

## 9. Commits

Short subject line, ASCII only, a brief body only when it adds something. The quality gate (`make check`
and `make test-all`) must pass before committing.
