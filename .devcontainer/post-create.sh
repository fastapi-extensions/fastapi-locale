#!/usr/bin/env bash
# Runs once after the container is created: installs the locked environment and checks the tools,
# so a broken setup fails here with a clear message instead of as a confusing test error later.
set -euo pipefail

VENV="${UV_PROJECT_ENVIRONMENT:-/home/vscode/.venv}"
CACHE="${UV_CACHE_DIR:-/home/vscode/.cache/uv}"

log() { printf '\n==> %s\n' "$*"; }
warn() { printf '    warning: %s\n' "$*"; }

log "Preparing volumes"
# Named volumes can be created root-owned; give them to the container user.
sudo chown -R "$(id -u):$(id -g)" "$VENV" "$CACHE" 2>/dev/null || true

log "Installing the locked environment"
uv sync --locked

log "Installing git hooks"
if git rev-parse --git-dir >/dev/null 2>&1; then
  uv run pre-commit install
else
  warn "not a git repository; skipped pre-commit install"
fi

log "Tool versions"
printf '    %s\n' "$("$VENV/bin/python" --version)" "$(uv --version)" \
  "$(uv run ruff --version)" "$(uv run mypy --version)"

log "Docker (needed only for make diagrams)"
if docker info >/dev/null 2>&1; then
  printf '    docker %s\n' "$(docker version --format '{{.Server.Version}}')"
else
  warn "docker is not reachable; make diagrams will not work"
fi

cat <<'MSG'

  Environment ready.

    make check      lint, types, layering, security
    make test-all   the whole test suite with coverage
    make docs       build the documentation site

MSG
