# ADR-0010: Project toolchain

- Status: Accepted
- Accepted: 2026-09-28
- Date: 2026-09-26

## Context

Contributors should be able to set up the project in minutes and get the same results locally and in CI.
The toolchain should match what the FastAPI community already uses, and what fastapi-tenancy uses in the
same organization.

## Decision

| Concern | Tool | Notes |
| --- | --- | --- |
| Environments, lock file, Python installs | uv | `uv sync` sets up everything; `uv.lock` is committed. |
| Build backend | hatchling | Same as fastapi-tenancy. |
| Built-in error catalogs | shipped as `.po` source | Compiled in memory at setup, which takes milliseconds for a few hundred messages. No binaries are committed and editable installs never see stale `.mo` files. |
| Lint and format | Ruff | One tool for both. |
| Type checking | mypy in strict mode | The package ships `py.typed` (C-05). |
| Layering rules | import-linter | Enforces the rules in the detailed design, section 3. |
| Security scan | bandit | Same as fastapi-tenancy. |
| Tests | pytest, pytest-cov, Hypothesis | Hypothesis for the header parser and tag normalization. |
| Benchmarks | pytest-benchmark | Checks the NFR-01 budget. |
| Task runner | Makefile over uv | Same targets as fastapi-tenancy (`make check`, `make test`, ...). |
| End-to-end tests | pytest with a real Uvicorn process and httpx | The library has no external services, so no containers are needed at runtime. |
| Git hooks | pre-commit | Runs Ruff, mypy, markdownlint and the diagram check. |
| Documentation site | MkDocs Material with mkdocstrings | Same stack as FastAPI's own docs; hosted on Read the Docs. |
| Diagrams | PlantUML, pinned Docker image | Sources in `docs/diagrams`, rendered to SVG by `scripts/render-diagrams.sh`. |
| CI | GitHub Actions | Lint, type check, tests across the version matrix, docs build, diagram freshness. |
| Security | CodeQL, Dependabot, PyPI trusted publishing | No long-lived PyPI tokens. |
| Development environment | Dev container | Python, uv, Java and Graphviz for PlantUML, pre-commit installed. |

The minimum Python version is 3.11 (SRS section 7, OI-01).

## Consequences

- One command to set up (`uv sync`) and one to check everything (`uv run pre-commit run --all-files`).
- Committed SVG diagrams render on GitHub and in the docs without PlantUML installed; CI fails if an SVG is
  older than its source.
- The development guide describes the day-to-day workflow in detail.

## Related requirements

C-05, NFR-08, NFR-11, NFR-13, NFR-14
