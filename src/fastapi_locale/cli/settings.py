"""Command line settings, read from ``[tool.fastapi-locale]`` in ``pyproject.toml``."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["Settings", "SettingsError", "load_settings"]


class SettingsError(Exception):
    """The command line settings are missing or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Where sources and catalogs live."""

    root: Path
    sources: tuple[Path, ...]
    locales_dir: Path
    domain: str = "messages"
    locales: tuple[str, ...] = field(default=())

    @property
    def template(self) -> Path:
        """Path of the extracted template."""
        return self.locales_dir / f"{self.domain}.pot"

    def catalog(self, directory_name: str) -> Path:
        """Path of one language's ``.po`` file."""
        return self.locales_dir / directory_name / "LC_MESSAGES" / f"{self.domain}.po"

    def catalogs(self) -> list[Path]:
        """Every ``.po`` file of the domain, sorted."""
        return sorted(self.locales_dir.glob(f"*/LC_MESSAGES/{self.domain}.po"))


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

    root = path.resolve().parent
    sources = section.get("sources", ["."])
    locales = section.get("locales", [])
    domain = section.get("domain", "messages")
    locales_dir = section.get("locales_dir", "locales")
    if not (_strings(sources) and _strings(locales) and isinstance(domain, str)):
        msg = "sources and locales must be lists of strings, domain must be a string"
        raise SettingsError(msg)
    if not isinstance(locales_dir, str):
        msg = "locales_dir must be a string"
        raise SettingsError(msg)
    return Settings(
        root=root,
        sources=tuple(root / source for source in sources),
        locales_dir=root / locales_dir,
        domain=domain,
        locales=tuple(locales),
    )


def _strings(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)
