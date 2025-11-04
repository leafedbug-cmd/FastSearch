from __future__ import annotations

import sys
from pathlib import Path
import typer

from fastsearch.gui.app import run_gui

app = typer.Typer(help="FastSearch CLI")


@app.command()
def gui() -> None:
    """Launch the FastSearch GUI."""
    run_gui()


if __name__ == "__main__":
    sys.exit(app())

