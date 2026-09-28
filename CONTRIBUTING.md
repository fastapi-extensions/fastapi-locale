# Contributing

Thanks for helping. Bug reports, translations, documentation and code are all welcome.

## Before you start

- For anything larger than a small fix, open an issue first so we can agree on the approach.
- Design decisions are recorded in
  [docs/adr](https://github.com/fastapi-extensions/fastapi-locale/blob/main/docs/adr/README.md).
  If your change goes against one, propose a new ADR in the same pull request.

## Set up

See the
[development guide](https://github.com/fastapi-extensions/fastapi-locale/blob/main/docs/development/development-guide.md).
In short:

```sh
make dev         # locked environment and git hooks
make check       # static checks
make test-all    # whole test suite with coverage
```

## Pull requests

- Keep each pull request to one change.
- Add tests at the lowest level that proves the behaviour.
- Update the docs and `CHANGELOG.md` when behaviour changes.
- Re-render diagrams with `make diagrams` if you changed a `.puml` file.

## Translations

Built-in error messages live in `src/fastapi_locale/locales/<language>/LC_MESSAGES/fastapi_locale.po`.
To add a language, run `uv run python scripts/sync_error_catalog.py --init <tag>`, translate the new file
in any gettext editor, and open a pull request. Keep every `{placeholder}` from the English text.

## Conduct

Be kind and assume good intent. Harassment of any kind is not tolerated.
