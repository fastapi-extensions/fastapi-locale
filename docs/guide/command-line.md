# Command line tool

`fastapi-locale` reads its settings from `[tool.fastapi-locale]` in `pyproject.toml`:

| Key | Default | Meaning |
| --- | --- | --- |
| `sources` | `["."]` | Directories scanned for messages. Each must exist. |
| `catalog_dir` | `"locales"` | Where the templates and the catalogs live. Use the same directory in `catalog_dirs`. |
| `default_domain` | `"messages"` | Domain of `gettext()` and the other functions without a `d`. Use the same value as in `LocaleConfig`. |
| `exclude` | `[]` | Paths to leave out, as glob patterns matched against the end of the path, such as `"tests"` or `"*_pb2.py"`. |

A key the tool does not know is an error, so a typing mistake cannot go unnoticed. Pass
`--config path/to/pyproject.toml` to use another file, and `--version` to print the installed version.

| Command | What it does |
| --- | --- |
| `extract` | Scan the sources and write one template per domain, `<catalog_dir>/<domain>.pot`. Comments starting with `Translators:` are passed to translators. |
| `init --locale TAG` | Create the catalogs for a new language, with its CLDR plural rules. |
| `update` | Merge each template into every catalog of its domain. |
| `compile` | Build a `.mo` file from every `.po` file. `--strict` fails on fuzzy entries instead of skipping them. |
| `check` | Change nothing; report problems. `--require-complete` also fails on untranslated entries. |

## What is scanned

Every `.py` file under the source directories, except hidden directories, `__pycache__`, `node_modules`,
`site-packages`, virtual environments (any directory with a `pyvenv.cfg`), and paths matching `exclude`.

The extractor recognizes `gettext`, `ngettext`, `pgettext`, `npgettext`, their `d` and `_lazy` variants,
`gettext_noop` and `_`, called as functions or as methods of a translator. Only string literals can be
extracted.

A template is rewritten only when its content changes, so running `extract` again leaves no diff.

## Domains

A message goes to the template of its domain. `gettext("Orders")` is written to `messages.pot`, and
`dgettext("admin", "Dashboard")` to `admin.pot`. The domain must be a string literal; a call that passes
a variable is reported and skipped. `init`, `update`, `compile` and `check` work on every domain.

A catalog without a template is compiled and checked too. That is how an override of the library's own
messages, `fastapi_locale.po`, is built; see [validation errors](validation-errors.md#overriding-a-message).

## Checking in CI

`check` fails when a template is out of date with the code, a catalog misses messages, an entry is
fuzzy, a catalog has no `Plural-Forms` header, or a translation uses a placeholder the message does not
have. Run it in CI:

```yaml
- run: uv run fastapi-locale check
```

Exit codes: 0 success, 1 problems found, 2 configuration or usage error.

Commit the `.po` files and build `.mo` files in CI or when packaging; `.mo` files are build output.
