# ADR-0015: Format the documentation site's own assets with Prettier

- Status: Accepted
- Accepted: 2026-10-04
- Date: 2026-10-04

## Context

The documentation site now carries a stylesheet and a script of its own. They keep identifiers whole in
tables, bring link, tab and footer colours up to WCAG AA, and let readers open a diagram at full size.
ADR-0010 names Ruff for Python and markdownlint for Markdown; nothing in the toolchain formats HTML, CSS
or JavaScript.

## Options considered

1. **Prettier.** The formatter most projects use for these three languages, with no configuration to
   speak of.
2. **Biome.** Fast and a single binary, but its HTML formatting is newer and less widely used.
3. **No formatter.** Two small files do not need one today, but style drifts as soon as a second person
   edits them.

## Decision

Use option 1.

- Prettier is pinned in `.pre-commit-config.yaml` and runs in the Node environment that pre-commit
  manages, so contributors and CI need no global Node tools.
- It formats `docs/**/*.{html,css,js}` and nothing else. `.prettierignore` states the same scope for
  editors, so Prettier never touches Markdown, YAML or generated files.
- The commit hook writes the formatting. `make fmt` does the same, and `make lint`, which CI runs, only
  checks it.

## Consequences

- The site's assets are formatted the same way everywhere, with one pinned version.
- Updating Prettier is a one-line change to the pin.
- Theme template overrides are Jinja, not plain HTML. If the site ever adds them, they need a
  template-aware formatter or an exclusion.

## Related requirements

NFR-11, NFR-13
