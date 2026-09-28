# Deployment

## Build catalogs in CI

Commit the `.po` files and compile them when you build the application:

```yaml
- run: uv run fastapi-locale check      # fail on stale or broken catalogs
- run: uv run fastapi-locale compile    # write the .mo files the application loads
```

In a container image, compile in the build stage so the `.mo` files are part of the image:

```dockerfile
COPY . /app
RUN uv sync --locked --no-dev && uv run fastapi-locale compile
```

The library's own error catalogs ship inside the package and need no build step.

## Startup

Catalogs are read once, when the application module creates its `Localization`. A missing directory or a
corrupt file raises `CatalogLoadError`, so a broken deployment fails at startup, not on the first request.
Nothing is read from disk while serving requests.

## Workers

Each worker process loads its own read-only copy of the catalogs. Workers share nothing, so running more
workers (`uvicorn --workers 4`, Gunicorn, Kubernetes replicas) needs no configuration.

## Caches and CDNs

Every response carries `Content-Language` and a `Vary` header naming the request headers that chose the
locale, usually `Accept-Language` and `Cookie`. Shared caches that honour `Vary` keep one copy per
language.

Many CDNs ignore `Vary` or treat `Vary: Cookie` as uncacheable. For cached pages, prefer a locale in the
URL (the `lang` query parameter, or a path prefix in your own routing) and configure the CDN to include it
in the cache key.

## Logging

The library logs under the `fastapi_locale` logger:

| Level | Event |
| --- | --- |
| INFO | Catalogs loaded at startup: locales, domains, message count |
| WARNING | A supported locale has no catalog; a translation uses a placeholder without a value; a custom locale source raised |
| DEBUG | The locale chosen for each request and the source that chose it |

Request headers and message values are never logged above DEBUG. The chosen locale and its source are
available as `request.state.locale.locale` and `request.state.locale.decided_by` for your own access logs.
