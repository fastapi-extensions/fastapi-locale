# Development image for fastapi-locale: Python, uv and the tools the test suite and docs need.
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# uv is copied from its official image, pinned so every contributor gets the same version.
COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /uvx /usr/local/bin/

# gettext gives msgfmt and msgunfmt for inspecting catalogs by hand; not needed by the tests.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/*
