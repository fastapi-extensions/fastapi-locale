"""Command line settings, read from ``[tool.fastapi-locale]`` in ``pyproject.toml``."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["DOMAIN", "Settings", "SettingsError", "load_settings"]

# A domain becomes a file name, so it is limited to characters that are safe in one.
DOMAIN = re.compile(r"[A-Za-z0-9_.-]+")
_KEYS = ("catalog_dir", "default_domain", "exclude", "sources")


class SettingsError(Exception):
    """The command line settings are missing or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Where sources and catalogs live."""

    root: Path
    sources: tuple[Path, ...]
    catalog_dir: Path
    default_domain: str = "messages"
    exclude: tuple[str, ...] = field(default=())

    def template(self, domain: str) -> Path:
        """Path of the template of one domain."""
        return self.catalog_dir / f"{domain}.pot"

    def templates(self) -> list[Path]:
        """Every template in the catalog directory, sorted."""
        return sorted(self.catalog_dir.glob("*.pot"))

    def catalog(self, directory_name: str, domain: str) -> Path:
        """Path of one language's ``.po`` file for a domain."""
        return self.catalog_dir / directory_name / "LC_MESSAGES" / f"{domain}.po"

    def catalogs(self, domain: str = "*") -> list[Path]:
        """Every ``.po`` file, or those of one domain, sorted."""
        return sorted(self.catalog_dir.glob(f"*/LC_MESSAGES/{domain}.po"))


def load_settings(config: Path | None = None) -> Settings:
    """Load settings from ``config`` or from ``pyproject.toml`` in the current directory."""
    path = config or Path("pyproject.toml")
    if not path.is_file():
        msg = f"{path} not found; run from the project root or pass --config"
        raise SettingsError(msg)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        msg = f"{path} is not valid TOML: {exc}"
        raise SettingsError(msg) from exc
    section: object = data.get("tool", {}).get("fastapi-locale")
    if not isinstance(section, dict):
        msg = f"{path} has no [tool.fastapi-locale] section"
        raise SettingsError(msg)
    unknown = sorted(set(section) - set(_KEYS))
    if unknown:
        msg = f"unknown setting {unknown[0]!r}; the settings are {', '.join(_KEYS)}"
        raise SettingsError(msg)

    sources = section.get("sources", ["."])
    exclude = section.get("exclude", [])
    domain = section.get("default_domain", "messages")
    catalog_dir = section.get("catalog_dir", "locales")
    if not (_strings(sources) and _strings(exclude)):
        msg = "sources and exclude must be lists of strings"
        raise SettingsError(msg)
    if not isinstance(catalog_dir, str):
        msg = "catalog_dir must be a string"
        raise SettingsError(msg)
    if not isinstance(domain, str) or not DOMAIN.fullmatch(domain):
        msg = "default_domain must be a name made of letters, digits, _ - ."
        raise SettingsError(msg)

    root = path.resolve().parent
    directories = tuple(root / source for source in sources)
    for directory in directories:
        # A mistyped directory would otherwise yield an empty template without any complaint.
        if not directory.is_dir():
            msg = f"sources entry is not a directory: {directory}"
            raise SettingsError(msg)
    return Settings(
        root=root,
        sources=directories,
        catalog_dir=root / catalog_dir,
        default_domain=domain,
        exclude=tuple(exclude),
    )


def _strings(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)
