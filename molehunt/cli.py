"""Command-line entry point. Commands are added as their engine phases land."""

from molehunt import __version__

import typer

app = typer.Typer(
    name="molehunt",
    help="Synthetic document forensics and casebook.",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Print the installed MoleHunt version."""
    typer.echo(f"MoleHunt {__version__}")


if __name__ == "__main__":
    app()


def main() -> None:
    """Run the command-line application."""
    app()
