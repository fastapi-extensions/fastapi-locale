"""The ``fastapi-locale`` command: extract, init, update, compile and check catalogs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi_locale.cli.commands import check, compile_catalogs, extract, init, update
from fastapi_locale.cli.settings import SettingsError, load_settings

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastapi_locale.cli.commands import Report

__all__ = ["main"]

EXIT_OK = 0
EXIT_PROBLEMS = 1
EXIT_USAGE = 2


def build_parser() -> argparse.ArgumentParser:
    """Command line interface definition."""
    parser = argparse.ArgumentParser(
        prog="fastapi-locale",
        description="Maintain gettext catalogs for a FastAPI application.",
    )
    parser.add_argument(
        "--config", type=Path, help="pyproject.toml to read (default: ./pyproject.toml)"
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    commands.add_parser("extract", help="write the template from the sources")
    init_parser = commands.add_parser("init", help="start the catalog of a new language")
    init_parser.add_argument(
        "--locale", required=True, help="language tag, for example hi or pt-BR"
    )
    commands.add_parser("update", help="merge the template into every catalog")
    compile_parser = commands.add_parser("compile", help="compile every catalog to .mo")
    compile_parser.add_argument("--strict", action="store_true", help="fail on fuzzy entries")
    check_parser = commands.add_parser("check", help="report problems without changing files")
    check_parser.add_argument(
        "--require-complete", action="store_true", help="treat untranslated entries as errors"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line tool and return its exit code."""
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings(args.config)
    except SettingsError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return EXIT_USAGE

    out = sys.stdout
    report: Report
    if args.command == "extract":
        report = extract(settings, out)
    elif args.command == "init":
        report = init(settings, args.locale, out)
    elif args.command == "update":
        report = update(settings, out)
    elif args.command == "compile":
        report = compile_catalogs(settings, out, strict=args.strict)
    else:
        report = check(settings, require_complete=args.require_complete)
        if not report.errors:
            out.write("catalogs are up to date\n")
    report.write(out)
    return EXIT_PROBLEMS if report.errors else EXIT_OK
