"""Shared Typer application objects and small helpers for the CLI modules.

Commands live in ``cli_lab`` (key, masters, copies, analysis), ``cli_evidence``
(custody, intake, report), and ``cli_bench`` (benchmark, Red Team). ``cli.py``
imports them so every command registers on the one ``app`` below.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import NoReturn

import typer

from molehunt.core.keys import KEY_BYTES

app = typer.Typer(
    name="molehunt",
    help="Synthetic document forensics and casebook.",
    no_args_is_help=True,
)
custody_app = typer.Typer(help="Append, verify, and demonstrate the custody hash chain.")
app.add_typer(custody_app, name="custody")

DEFAULT_KEY = Path(".molehunt/master.key")
DEFAULT_DB = Path(".molehunt/molehunt.sqlite3")
DEFAULT_CUSTODY_LOG = Path(".molehunt/custody.log")
DEFAULT_MASTERS = Path("data/masters")


def fail(error: BaseException, code: int = 2) -> NoReturn:
    """Print an error on stderr and exit with ``code``."""
    typer.echo(f"Error: {error}", err=True)
    raise typer.Exit(code=code) from error


def read_key(path: Path) -> bytes:
    """Read and length-check the examiner key file."""
    key = path.read_bytes()
    if len(key) != KEY_BYTES:
        raise ValueError(f"key file must contain {KEY_BYTES} bytes")
    return key


def read_employee_ids(path: Path) -> list[str]:
    """Read synthetic employee IDs from a CSV file with an ``id`` column."""
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames or "id" not in reader.fieldnames:
                raise ValueError("employee CSV must have an 'id' column")
            employee_ids = [
                row.get("id", "").strip() for row in reader if row.get("id", "").strip()
            ]
    except OSError as error:
        raise ValueError(f"cannot read employee CSV: {path}") from error
    if not employee_ids:
        raise ValueError("employee CSV contains no IDs")
    if len(set(employee_ids)) != len(employee_ids):
        raise ValueError("employee IDs must be unique")
    return employee_ids


def split_list(value: str, cast=str) -> list:
    """Parse a comma-separated option into typed values."""
    return [cast(item.strip()) for item in value.split(",") if item.strip()]
