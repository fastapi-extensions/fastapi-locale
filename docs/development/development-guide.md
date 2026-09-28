# Development guide

| Field | Value |
| --- | --- |
| Document | Development guide |
| Version | 1.1 |
| Status | Approved |
| Owner | Kapil Dagur |
| Last updated | 2026-09-28 |

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
| Package | Builds the wheel and sdist and runs `scripts/check-dist.sh` |
| Performance budget | Benchmarks |
| Documentation and diagrams | Strict docs build; rendered diagrams match their sources |

CI also runs every Monday to catch breaking upstream releases, and CodeQL and dependency review run on
pull requests.

## 8. Releasing

### One-time setup

These steps need account access and are done once, by a maintainer.

**PyPI trusted publishing.** The project does not exist on PyPI before the first upload, so add a
*pending* publisher on both indexes (Account settings, Publishing, "Add a new pending publisher"):

| Field | pypi.org | test.pypi.org |
| --- | --- | --- |
| PyPI project name | `fastapi-locale` | `fastapi-locale` |
| Owner | `fastapi-extensions` | `fastapi-extensions` |
| Repository name | `fastapi-locale` | `fastapi-locale` |
| Workflow name | `release.yml` | `release.yml` |
| Environment name | `pypi` | `testpypi` |

No API token is created or stored anywhere.

**GitHub environments.** Already configured: `testpypi` and `pypi` accept deployments only from `v*`
tags, and `pypi` waits for a maintainer's approval before publishing.

**Read the Docs.** Import `fastapi-extensions/fastapi-locale` at readthedocs.org. The build is defined by
`.readthedocs.yaml`; enable "Build pull requests" so each pull request gets a preview.

### Release checklist

1. Native speakers have reviewed any new or changed built-in translations.
2. `version` in `pyproject.toml` is updated, and `CHANGELOG.md` has a section `## [X.Y.Z]` with the date;
   the `Unreleased` entries move into it.
3. The change is merged to `main` through a pull request with every required check green.
4. For a pre-release, tag `vX.Y.ZrcN` first and check the package on TestPyPI:
   `uv pip install -i https://test.pypi.org/simple/ fastapi-locale==X.Y.ZrcN`.
5. Tag the release and push the tag:

    ```sh
    git tag -a vX.Y.Z -m "fastapi-locale X.Y.Z"
    git push origin vX.Y.Z
    ```

6. Approve the `pypi` deployment in the Actions tab when the workflow asks.

### What the release workflow does

| Job | Checks |
| --- | --- |
| Validate the tag | The tag is `vX.Y.Z` or `vX.Y.Z(a,b,rc)N`, matches `pyproject.toml`, has a `CHANGELOG.md` section, and points at a commit on `main`. |
| Test and build | The whole test suite, then `uv build` and `scripts/check-dist.sh`: metadata renders on PyPI, the wheel has `py.typed` and the built-in catalogs and no build output, and it installs into a clean environment and localizes a 422. |
| Publish | Uploads with trusted publishing and PEP 740 attestations; waits for approval on `pypi`. |
| Install from the index | Installs the exact version back from PyPI or TestPyPI and imports it, retrying while the index catches up. |
| GitHub release | Creates the release from the changelog section and attaches the files; pre-releases are marked as such. |

A failure in any job stops the ones after it, so a GitHub release only exists for a version that installs.
The same `scripts/check-dist.sh` runs in CI on every pull request (the Package job), so packaging problems
show up long before a tag.

### Branch protection

`main` requires a pull request and every CI check (lint, types, layering, security, the test matrix, the
lowest dependency versions, macOS, Windows, the performance budget, and the docs). History is linear and
force pushes are blocked. When CI jobs are renamed, update the required checks in the repository
settings.

## 9. Commits

Short subject line, ASCII only, a brief body only when it adds something. The quality gate (`make check`
and `make test-all`) must pass before committing.
