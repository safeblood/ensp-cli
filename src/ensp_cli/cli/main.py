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
from ensp_cli.output import output_json
from ensp_cli.parser.topology_parser import TopologyParser, TopologyParserError

# Import commands
from ensp_cli.commands.config import (
    show_config_command,
    show_interfaces_command,
    show_routes_command,
)
from ensp_cli.commands.console import console_command
from ensp_cli.commands.exec import exec_batch_command, exec_command


class OutputFormat(str, Enum):
    """Output format options."""
    TABLE = "table"
    JSON = "json"

# Create the main Typer app
app = typer.Typer(
    name="ensp-cli",
    help="CLI tool for managing eNSP topology files and device connections",
    no_args_is_help=True,
    rich_markup_mode="rich",
    epilog="""
[bold]Examples:[/bold]
  ensp-cli list topology.topo
  ensp-cli console Router1
  ensp-cli exec Router1 "display version"

[bold]Exit Codes:[/bold]
  0 - Success
  1 - General error
  2 - File not found
  3 - Invalid XML / Parse error
  4 - Permission denied
  5 - Command timeout

For more information, visit: https://github.com/user/ensp-cli
"""
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


# Register commands
app.command(name="console")(console_command)
app.command(name="exec")(exec_command)
app.command(name="exec-batch")(exec_batch_command)
app.command(name="show-config")(show_config_command)
app.command(name="show-interfaces")(show_interfaces_command)
app.command(name="show-routes")(show_routes_command)


def _output_json(topology: Topology) -> None:
    """Output topology as JSON."""
    data = {
        "status": "success",
        "name": topology.name,
        "devices": [device.model_dump() for device in topology.devices],
        "connections": [conn.model_dump() for conn in topology.connections],
    }
    output_json(data)


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


def _output_visual(topology: Topology) -> None:
    """Output topology as ASCII art diagram with coordinate-based layout."""
    if not topology.devices:
        console.print("[yellow]No devices found in topology.[/yellow]")
        return
    
    # Create header
    console.print(f"\n[bold cyan]Topology: {topology.name}[/bold cyan]")
    console.print(f"[dim]Devices: {topology.device_count} | Connections: {topology.connection_count}[/dim]\n")
    
    # Check if we have coordinates
    devices_with_coords = [d for d in topology.devices if d.x is not None and d.y is not None]
    
    if len(devices_with_coords) >= 2:
        # Use coordinate-based layout
        _output_coordinate_visual(topology, devices_with_coords)
    else:
        # Fall back to list layout
        _output_list_visual(topology)


def _output_list_visual(topology: Topology) -> None:
    """Output topology as list when no coordinates available."""
    # Get devices sorted by type
    sorted_devices = sorted(topology.devices, 
                           key=lambda d: (0 if d.device_type == "Router" else 
                                        1 if d.device_type == "Switch" else 2))
    
    console.print("[bold]Network Topology:[/bold]\n")
    
    # Track drawn connections to avoid duplicates
    drawn_connections = set()
    
    for device in sorted_devices:
        # Get icon based on device type
        if device.device_type == "Router":
            icon = "[yellow](@)[/yellow]"
        elif device.device_type == "Switch":
            icon = "[green][#][/green]"
        elif device.device_type == "Cloud":
            icon = "[blue](~)[/blue]"
        else:
            icon = "[white](*)[/white]"
        
        # Find connections for this device
        outgoing = []
        for conn in topology.connections:
            if conn.from_device == device.name:
                conn_key = tuple(sorted([conn.from_device, conn.to_device]))
                if conn_key not in drawn_connections:
                    outgoing.append((conn.to_device, conn.from_port, conn.to_port))
                    drawn_connections.add(conn_key)
        
        console.print(f"  {icon} [bold]{device.name}[/bold] [dim]({device.device_type})[/dim]")
        
        for target, local_port, remote_port in outgoing:
            console.print(f"      |")
            console.print(f"      +--[yellow]{local_port}[/yellow]------[yellow]{remote_port}[/yellow]---> {target}")
        
        console.print()
    
    # Summary
    console.print("[bold]Summary:[/bold]")
    for device in sorted_devices:
        port_info = f" | Console Port: {device.console_port}" if device.console_port > 1 else ""
        console.print(f"  - [cyan]{device.name}[/cyan] - {device.device_type}{port_info}")
    
    console.print()


def _output_coordinate_visual(topology: Topology, devices: list) -> None:
    """Output topology using coordinate-based ASCII layout.
    
    Args:
        topology: The topology to display.
        devices: List of devices with coordinates.
    """
    # Find coordinate bounds
    min_x = min(d.x for d in devices)
    max_x = max(d.x for d in devices)
    min_y = min(d.y for d in devices)
    max_y = max(d.y for d in devices)
    
    # Grid dimensions (leave margins for labels)
    grid_width = 80
    grid_height = 20
    
    # Scale factors
    x_range = max_x - min_x if max_x != min_x else 1
    y_range = max_y - min_y if max_y != min_y else 1
    
    # Map coordinates to grid positions
    # eNSP Y coordinates: smaller Y = higher up on screen
    # Grid rows: smaller row number = higher up on screen
    # So we map directly without inversion
    def map_x(x: float) -> int:
        return int(4 + (x - min_x) / x_range * (grid_width - 15))
    
    def map_y(y: float) -> int:
        return int(2 + (y - min_y) / y_range * (grid_height - 6))
    
    # Create grid
    grid = [[" " for _ in range(grid_width)] for _ in range(grid_height)]
    
    # Device icons (using ASCII-safe chars, avoiding Rich markup brackets)
    icon_map = {
        "Router": "(@)",
        "Switch": "<#>",
        "Cloud": "{~}",
        "Firewall": "<X>",
    }
    
    # Calculate device positions first
    device_positions = {}
    for device in devices:
        gx = map_x(device.x)
        gy = map_y(device.y)
        device_positions[device.name] = (gx, gy)
    
    # Draw connections FIRST (so devices appear on top)
    drawn_conns = set()
    for conn in topology.connections:
        if conn.from_device in device_positions and conn.to_device in device_positions:
            # Avoid duplicate connections
            conn_key = tuple(sorted([conn.from_device, conn.to_device]))
            if conn_key in drawn_conns:
                continue
            drawn_conns.add(conn_key)
            
            x1, y1 = device_positions[conn.from_device]
            x2, y2 = device_positions[conn.to_device]
            
            # Draw line between device centers
            _draw_connection(grid, x1 + 1, y1, x2 + 1, y2)
    
    # Place devices on grid (ON TOP of connections)
    for device in devices:
        gx, gy = device_positions[device.name]
        icon = icon_map.get(device.device_type, "(*)")
        
        # Draw icon (overwrites any line characters)
        for i, char in enumerate(icon):
            if gx + i < grid_width:
                grid[gy][gx + i] = char
        
        # Draw device name below icon
        name_start = max(0, gx - len(device.name) // 2 + 1)
        for i, char in enumerate(device.name[:8]):  # Limit name length
            if name_start + i < grid_width and gy + 1 < grid_height:
                grid[gy + 1][name_start + i] = char
    
    # Print grid
    console.print("[bold]Network Topology (Coordinate Layout):[/bold]\n")
    for row in grid:
        line = "".join(row)
        # Replace trailing spaces but keep leading spaces for alignment
        line_stripped = line.rstrip()
        if line_stripped:
            console.print("  " + line_stripped)
    
    # Print legend
    console.print("\n[bold]Legend:[/bold]")
    from rich.text import Text
    
    legend_items = [
        ("(@)", "yellow", "Router"),
        ("<#>", "green", "Switch"),
        ("{~}", "blue", "Cloud"),
        ("<X>", "red", "Firewall"),
    ]
    for icon, color, dtype in legend_items:
        text = Text()
        text.append(f"  {icon} ", style=color)
        text.append(f"= {dtype}")
        console.print(text)
    
    # Print device details
    console.print("\n[bold]Device Details:[/bold]")
    for device in devices:
        port_info = f" | Port: {device.console_port}" if device.console_port > 1 else ""
        console.print(f"  {device.name}: ({device.device_type}){port_info} @ ({device.x:.0f}, {device.y:.0f})")
    
    console.print()


def _draw_connection(grid: list, x1: int, y1: int, x2: int, y2: int) -> None:
    """Draw a simple connection line between two points.
    
    Args:
        grid: The 2D grid to draw on.
        x1, y1: Start position.
        x2, y2: End position.
    """
    height = len(grid)
    width = len(grid[0]) if grid else 0
    
    # Simple line drawing - Bresenham-like
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    
    if dx == 0 and dy == 0:
        return
    
    steps = max(dx, dy)
    x, y = x1, y1
    x_inc = (x2 - x1) / steps
    y_inc = (y2 - y1) / steps
    
    for step in range(steps + 1):
        gx, gy = int(round(x)), int(round(y))
        if 0 <= gx < width and 0 <= gy < height:
            # Only draw if space is empty (don't overwrite device icons/names)
            if grid[gy][gx] == " ":
                # Determine line character
                if abs(x_inc) > abs(y_inc) * 2:
                    grid[gy][gx] = "-"
                elif abs(y_inc) > abs(x_inc) * 2:
                    grid[gy][gx] = "|"
                elif abs(x_inc) > 0 and abs(y_inc) > 0:
                    # Diagonal
                    if (x2 > x1 and y2 > y1) or (x2 < x1 and y2 < y1):
                        grid[gy][gx] = "\\"
                    else:
                        grid[gy][gx] = "/"
        x += x_inc
        y += y_inc


def _find_topology_file() -> Optional[Path]:
    """Auto-discover .topo file in current directory.
    
    Returns:
        Path to the .topo file if exactly one is found, None otherwise.
    """
    cwd = Path.cwd()
    topo_files = [f for f in cwd.glob("*.topo")]
    
    if len(topo_files) == 1:
        return topo_files[0]
    return None


@app.command()
def list(
    topo_file: Optional[Path] = typer.Argument(
        None,
        help="Path to the .topo file to parse (auto-discovers if not specified)",
        exists=True,
        readable=True,
        dir_okay=False,
        resolve_path=True,
    ),
    output: str = typer.Option(
        "table",
        "--output",
        "-o",
        help="Output format (table, json, or visual)",
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
    
    If no topology file is specified, auto-discovers .topo files
    in the current directory. Uses the file if exactly one is found.
    
    Examples:
        ensp-cli list                    # Auto-discover
        ensp-cli list topology.topo
        ensp-cli list topology.topo --output json
        ensp-cli list topology.topo --output visual
        ensp-cli list topology.topo --show-connections
    
    Exit codes:
        0: Success
        2: File not found
        3: Parse error
        4: Permission denied
    """
    # Auto-discover if not specified
    if topo_file is None:
        topo_file = _find_topology_file()
        if topo_file:
            console.print(f"[dim]Auto-discovered: {topo_file.name}[/dim]")
        else:
            console.print("[red]Error: No topology file specified and auto-discovery failed.[/red]")
            console.print("[yellow]Please specify a .topo file or ensure exactly one exists in the current directory.[/yellow]")
            raise typer.Exit(2)
    
    try:
        parser = TopologyParser()
        topology = parser.parse_file(topo_file)
        
        if output == "json":
            _output_json(topology)
        elif output == "visual":
            _output_visual(topology)
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
