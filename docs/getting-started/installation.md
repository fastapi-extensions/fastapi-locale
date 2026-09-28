<!-- markdownlint-disable MD046 - content tabs indent their fenced code blocks -->

# Installation

fastapi-locale needs Python 3.11 or later and works with FastAPI 0.115 or later and Pydantic 2.

=== "uv"

    ```sh
    uv add fastapi-locale
    ```

=== "pip"

    ```sh
    pip install fastapi-locale
    ```

This installs the library, its only other dependency [Babel](https://babel.pocoo.org), and the
`fastapi-locale` command line tool.

## Check the installation

```sh
fastapi-locale --help
```

## Translation tools

Catalogs are plain gettext `.po` files. Translators can use any gettext editor, for example
[Poedit](https://poedit.net) on the desktop or [Weblate](https://weblate.org) for teams. No special
tooling is needed on the translator's side.
