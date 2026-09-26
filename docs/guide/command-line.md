# Command line tool

`fastapi-locale` reads its settings from `[tool.fastapi-locale]` in `pyproject.toml`:

| Key | Default | Meaning |
| --- | --- | --- |
| `sources` | `["."]` | Directories scanned for messages. |
| `locales_dir` | `"locales"` | Where the template and the catalogs live. |
| `domain` | `"messages"` | Catalog file name. |

Pass `--config path/to/pyproject.toml` to use another file.

| Command | What it does |
| --- | --- |
| `extract` | Scan the sources and write `<locales_dir>/<domain>.pot`. Comments starting with `Translators:` are passed to translators. |
| `init --locale TAG` | Create the catalog for a new language, with its CLDR plural rules. |
| `update` | Merge the template into every catalog. |
| `compile` | Build `.mo` files. `--strict` fails on fuzzy entries instead of skipping them. |
| `check` | Change nothing; report problems. `--require-complete` also fails on untranslated entries. |

`check` fails when the template is out of date with the code, a catalog misses messages, an entry is
fuzzy, a catalog has no `Plural-Forms` header, or a translation uses a placeholder the message does not
have. Run it in CI:

```yaml
- run: uv run fastapi-locale check
```

Exit codes: 0 success, 1 problems found, 2 configuration or usage error.

Commit the `.po` files and build `.mo` files in CI or when packaging; `.mo` files are build output.
