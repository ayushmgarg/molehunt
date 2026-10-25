"""MoleHunt command-line entry point.

Importing the command modules registers their commands on the shared Typer
``app`` (see ``cli_app.py``): lab commands, evidence/custody commands, the
benchmark, and the live LAN games plus ``examine`` / ``forward``.
"""

from molehunt import cli_bench, cli_evidence, cli_lab, cli_live  # noqa: F401  (register)
from molehunt.cli_app import app

__all__ = ["app", "main"]


def main() -> None:
    """Run the command-line application."""
    app()


if __name__ == "__main__":
    main()
