"""Console command for interactive device sessions."""

import json
import sys
from pathlib import Path
from typing import Optional, Union

import typer
from rich.console import Console

from ensp_cli.connection_manager import device_session
from ensp_cli.interactive_session import InteractiveSession
from ensp_cli.models import Device, Topology
from ensp_cli.output import OutputFormat, output_error, output_json
from ensp_cli.parser.topology_parser import TopologyParser, TopologyParserError

console = Console()

app = typer.Typer()


def find_topology_file(path: Optional[Path] = None) -> Path:
    """Find topology file in given path or current directory.
    
    Args:
        path: Optional explicit path to topology file.
        
    Returns:
        Path to the topology file.
        
    Raises:
        FileNotFoundError: If topology file not found.
        ValueError: If multiple .topo files found.
    """
    if path:
        if not path.exists():
            raise FileNotFoundError(f"Topology file not found: {path}")
        return path
    
    # Search current directory for .topo files
    current_dir = Path.cwd()
    topo_files = list(current_dir.glob("*.topo"))
    
    if not topo_files:
        raise FileNotFoundError("No .topo file found in current directory")
    if len(topo_files) > 1:
        raise ValueError(
            f"Multiple .topo files found: {[f.name for f in topo_files]}. "
            "Use --topology to specify."
        )
    
    return topo_files[0]


def get_device_or_none(topology: Topology, device_name: str, output_format: str = "text") -> Device | None:
    """Find device or print error and return None.
    
    Args:
        topology: The topology to search in.
        device_name: The device name to search for.
        output_format: Output format (text or json) as string.
        
    Returns:
        The Device if found, None otherwise.
    """
    device = topology.get_device(device_name)
    if device is None:
        available = [d.name for d in topology.devices]
        fmt = OutputFormat.JSON if output_format == "json" else OutputFormat.TEXT
        if fmt == OutputFormat.JSON:
            output_json({
                "status": "error",
                "error": f"Device '{device_name}' not found in topology",
                "device": device_name,
                "available_devices": available,
            })
        else:
            console.print(f"[red]Error: Device '{device_name}' not found in topology.[/red]")
            console.print(f"[yellow]Available devices: {', '.join(available)}[/yellow]")
        return None
    return device


def parse_topology(topo_file: Path) -> Topology:
    """Parse topology file.
    
    Args:
        topo_file: Path to the topology file.
        
    Returns:
        Parsed Topology object.
        
    Raises:
        FileNotFoundError: If file not found.
        TopologyParserError: If parsing fails.
    """
    parser = TopologyParser()
    return parser.parse_file(topo_file)


async def console_async(
    device_name: str,
    topology_path: Optional[Path],
    output_format: Union[OutputFormat, str],
) -> int:
    """Async implementation of console command.
    
    Args:
        device_name: Name of the device to connect to.
        topology_path: Optional path to topology file.
        output_format: Output format (text or json).
        
    Returns:
        Exit code (0 for success, 1 for failure).
    """
    try:
        # Find and parse topology
        topo_file = find_topology_file(topology_path)
        topology = parse_topology(topo_file)
        
        # Find device
        output_format_str = output_format.value if isinstance(output_format, OutputFormat) else output_format
        device = get_device_or_none(topology, device_name, output_format_str)
        if device is None:
            return 1
        
        # Connect and start interactive session
        async with device_session(device) as client:
            if output_format_str == "json":
                output_json({
                    "status": "connected",
                    "device": device.name,
                    "address": f"127.0.0.1:{device.console_port}",
                    "device_type": device.device_type,
                    "model": device.model,
                })
            else:
                console.print(f"[green]Connected to {device.name} at 127.0.0.1:{device.console_port}[/green]")
                console.print("[dim]Press Ctrl+] or Ctrl+D to exit[/dim]")
                console.print("-" * 40)
            
            session = InteractiveSession(client)
            await session.start()
            
        return 0
        
    except FileNotFoundError as e:
        output_error(str(e), output_format)
        return 1
    except ValueError as e:
        output_error(str(e), output_format)
        return 1
    except ConnectionError as e:
        output_error(str(e), output_format)
        return 1
    except KeyboardInterrupt:
        if output_format != OutputFormat.JSON:
            console.print("\n[yellow]Disconnected.[/yellow]")
        return 0


@app.command(name="console")
def console_command(
    device_name: str = typer.Argument(..., help="Name of the device to connect to"),
    topology: Optional[Path] = typer.Option(
        None,
        "--topology",
        "-t",
        help="Path to topology file",
        exists=True,
        readable=True,
        dir_okay=False,
        resolve_path=True,
    ),
    output: OutputFormat = typer.Option(
        OutputFormat.TEXT,
        "--output",
        "-o",
        help="Output format (text or json)",
    ),
) -> None:
    """Open an interactive console session with a device.
    
    Connects to the specified device via Telnet and opens an interactive
    console session. The session can be terminated with Ctrl+] or Ctrl+D.
    
    Examples:
        ensp-cli console Router1
        ensp-cli console Router1 --topology mylab.topo
        ensp-cli console Router1 --output json
    
    Exit codes:
        0: Success or user disconnect
        1: Connection error or device not found
        2: Topology file not found
    """
    import asyncio
    
    exit_code = asyncio.run(console_async(device_name, topology, output))
    raise typer.Exit(exit_code)
