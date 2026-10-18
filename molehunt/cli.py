"""MoleHunt command-line entry point.

Importing the command modules registers their commands on the shared Typer
``app`` (see ``cli_app.py``): lab commands, evidence/custody commands, and the
benchmark.
"""

from molehunt import cli_bench, cli_evidence, cli_lab  # noqa: F401  (register commands)
from molehunt.cli_app import app

__all__ = ["app", "main"]


def main() -> None:
    """Run the command-line application."""
    app()


if __name__ == "__main__":
    main()
