"""Main CLI entry point for eNSP CLI."""

import json
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ensp_cli import __version__
from ensp_cli.models import Topology
from ensp_cli.parser.topology_parser import TopologyParser, TopologyParserError


class OutputFormat(str, Enum):
    """Output format options."""
    TABLE = "table"
    JSON = "json"

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


def _output_json(topology: Topology) -> None:
    """Output topology as JSON."""
    data = {
        "name": topology.name,
        "devices": [device.model_dump() for device in topology.devices],
        "connections": [conn.model_dump() for conn in topology.connections],
    }
    console.print(json.dumps(data, indent=2))


def _output_table(topology: Topology, show_connections: bool = False) -> None:
    """Output topology as table."""
    if show_connections:
        if not topology.connections:
            console.print("[yellow]No connections found in topology.[/yellow]")
            return
        
        table = Table(
            title=f"Connections in '{topology.name}'",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("From Device", style="cyan")
        table.add_column("From Port", style="green")
        table.add_column("To Device", style="blue")
        table.add_column("To Port", style="yellow")
        
        for conn in topology.connections:
            table.add_row(
                conn.from_device,
                conn.from_port,
                conn.to_device,
                conn.to_port,
            )
        
        console.print(table)
        console.print(f"\nTotal: {topology.connection_count} connection(s)")
    else:
        if not topology.devices:
            console.print("[yellow]No devices found in topology.[/yellow]")
            return
        
        table = Table(
            title=f"Devices in '{topology.name}'",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Model", style="blue")
        table.add_column("Console Port", justify="right", style="yellow")
        
        for device in topology.devices:
            table.add_row(
                device.name,
                device.device_type,
                device.model,
                str(device.console_port),
            )
        
        console.print(table)
        console.print(f"\nTotal: {topology.device_count} device(s)")


@app.command()
def list(
    topo_file: Path = typer.Argument(
        ...,
        help="Path to the .topo file to parse",
        exists=True,
        readable=True,
        dir_okay=False,
        resolve_path=True,
    ),
    output: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--output",
        "-o",
        help="Output format (table or json)",
    ),
    show_connections: bool = typer.Option(
        False,
        "--show-connections",
        "-c",
        help="Show connections instead of devices",
    ),
) -> None:
    """List devices in a topology file.
    
    Displays a table of all devices in the topology with their
    name, type, model, and console port information.
    
    Examples:
        ensp-cli list topology.topo
        ensp-cli list topology.topo --output json
        ensp-cli list topology.topo --show-connections
    """
    try:
        parser = TopologyParser()
        topology = parser.parse_file(topo_file)
        
        if output == OutputFormat.JSON:
            _output_json(topology)
        else:
            _output_table(topology, show_connections=show_connections)
        
    except FileNotFoundError:
        console.print(f"[red]Error: File not found: {topo_file}[/red]")
        raise typer.Exit(2)
    except PermissionError:
        console.print(f"[red]Error: Cannot read file: {topo_file}[/red]")
        raise typer.Exit(4)
    except TopologyParserError as e:
        console.print(f"[red]Error: Failed to parse topology file: {e}[/red]")
        raise typer.Exit(3)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
