"""Main CLI entry point for eNSP CLI."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ensp_cli import __version__

# Create the main Typer app
app = typer.Typer(
    name="ensp-cli",
    help="CLI tool for managing eNSP topology files and device connections",
    no_args_is_help=True,
)

console = Console()


def version_callback(value: bool) -> None:
    """Callback for --version flag."""
    if value:
        console.print(f"ensp-cli version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version information and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """eNSP CLI - Manage eNSP topology files and device connections.
    
    This tool provides commands to parse, inspect, and interact with
    Huawei eNSP (Enterprise Network Simulation Platform) topology files.
    
    Exit codes:
        0 - Success
        1 - General error
        2 - File not found
        3 - Invalid XML / Parse error
        4 - Permission denied
    """
    pass


if __name__ == "__main__":
    app()
