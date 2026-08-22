"""CLI surface: `memoir who`, `memoir audit`. P2 implements."""

import typer

app = typer.Typer(
    no_args_is_help=True, help="Find who most likely holds the mental model of a file."
)


@app.callback()
def _root() -> None:
    """memoir: git-history expert finder."""
