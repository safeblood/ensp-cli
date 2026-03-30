"""Config commands for displaying device configuration and status."""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

from ensp_cli.connection_manager import device_session
from ensp_cli.models import Device, Topology
from ensp_cli.parser.topology_parser import TopologyParser, TopologyParserError
from ensp_cli.services.config_exporter import ConfigExporter
from ensp_cli.services.config_importer import (
    ConfigImporter,
    ConfigImportError,
    DangerousCommandError,
    ImportResult,
)

# Import helper functions from console
from ensp_cli.commands.console import find_topology_file, get_device_or_none, parse_topology
from ensp_cli.commands.exec import execute_command

console = Console()

app = typer.Typer()


async def execute_show_command(
    device: Device,
    command: str,
    timeout: float = 10.0,
) -> str:
    """Execute a show command on a device and return the output.
    
    Args:
        device: The device to execute command on.
        command: The command to execute.
        timeout: Timeout in seconds for operations.
        
    Returns:
        Clean command output (without command echo or prompt).
    """
    return await execute_command(device, command, timeout)


def filter_config_section(config_output: str, section: str) -> str:
    """Filter configuration output for a specific section.
    
    Args:
        config_output: Full configuration output.
        section: Section name to filter (e.g., 'interface', 'ospf', 'bgp').
        
    Returns:
        Filtered configuration section.
    """
    lines = config_output.splitlines()
    filtered_lines = []
    in_section = False
    section_indent = None
    
    # Normalize section name for matching
    section_lower = section.lower()
    
    for line in lines:
        stripped = line.strip().lower()
        
        # Check if this line starts the section
        if stripped.startswith(section_lower):
            in_section = True
            section_indent = len(line) - len(line.lstrip())
            filtered_lines.append(line)
        elif in_section:
            # Check if we've exited the section (lower indent or empty line followed by new section)
            current_indent = len(line) - len(line.lstrip())
            if line.strip() and current_indent <= section_indent:
                # We've moved to a different top-level section
                in_section = False
                section_indent = None
            else:
                filtered_lines.append(line)
    
    return "\n".join(filtered_lines) if filtered_lines else f"# Section '{section}' not found"


async def show_config_async(
    device_name: str,
    topology_path: Optional[Path],
    section: Optional[str],
    output_format: str,
    timeout: float = 10.0,
) -> int:
    """Async implementation of show-config command.
    
    Args:
        device_name: Name of the device to connect to.
        topology_path: Optional path to topology file.
        section: Optional section to filter.
        output_format: Output format (text or json).
        timeout: Timeout in seconds for command execution.
        
    Returns:
        Exit code:
            0 - Success
            1 - General error
            2 - File not found
            3 - Parse error
            5 - Command timeout
    """
    try:
        # Find and parse topology
        topo_file = find_topology_file(topology_path)
        topology = parse_topology(topo_file)
        
        # Find device
        device = get_device_or_none(topology, device_name, output_format)
        if device is None:
            return 1
        
        # Execute command
        config_output = await execute_show_command(device, "display current-configuration", timeout)
        
        # Filter by section if specified
        if section:
            config_output = filter_config_section(config_output, section)
        
        # Output result
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "success",
                "device": device_name,
                "section": section,
                "output": config_output,
            }))
        else:
            # Text output with syntax highlighting
            console.print(f"[cyan]Configuration for {device_name}:[/cyan]")
            console.print("-" * 60)
            syntax = Syntax(config_output, "cisco", theme="monokai", line_numbers=False)
            console.print(syntax)
        
        return 0
        
    except FileNotFoundError as e:
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": str(e),
            }))
        else:
            console.print(f"[red]Error: {e}[/red]")
        return 2
    except ValueError as e:
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": str(e),
            }))
        else:
            console.print(f"[red]Error: {e}[/red]")
        return 1
    except TopologyParserError as e:
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": f"Failed to parse topology file: {e}",
            }))
        else:
            console.print(f"[red]Error: Failed to parse topology file: {e}[/red]")
        return 3
    except ConnectionError as e:
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": str(e),
            }))
        else:
            console.print(f"[red]Error: {e}[/red]")
        return 1
    except asyncio.TimeoutError:
        error_msg = f"Command timed out after {timeout} seconds"
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": error_msg,
            }))
        else:
            console.print(f"[red]Error: {error_msg}[/red]")
        return 5


@app.command(name="show-config")
def show_config_command(
    device: str = typer.Argument(..., help="Device name"),
    topo_file: Optional[Path] = typer.Option(
        None,
        "--topology",
        "-t",
        help="Path to topology file",
        exists=True,
        readable=True,
        dir_okay=False,
        resolve_path=True,
    ),
    section: Optional[str] = typer.Option(
        None,
        "--section",
        "-s",
        help="Filter section (e.g., 'interface', 'ospf')",
    ),
    output: str = typer.Option(
        "text",
        "--output",
        "-o",
        help="Output format: text, json",
    ),
    timeout: float = typer.Option(
        10.0,
        "--timeout",
        help="Command timeout in seconds",
    ),
) -> None:
    """Display device running configuration.
    
    Connects to the specified device via Telnet, retrieves the
    current configuration using 'display current-configuration'.
    
    Examples:
        ensp-cli show-config Router1
        ensp-cli show-config Router1 --section interface
        ensp-cli show-config Router1 --output json
        ensp-cli show-config Router1 -t mylab.topo
    
    Exit codes:
        0: Success
        1: General error or device not found
        2: Topology file not found
        3: Parse error
        5: Command timeout
    """
    exit_code = asyncio.run(show_config_async(device, topo_file, section, output, timeout))
    raise typer.Exit(exit_code)


def parse_interface_brief_output(output: str) -> list[dict]:
    """Parse 'display ip interface brief' output into structured data.
    
    Args:
        output: Raw command output.
        
    Returns:
        List of interface dictionaries.
    """
    interfaces = []
    lines = output.splitlines()
    
    # Skip header lines and look for data
    in_data_section = False
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines and headers
        if not stripped or "Interface" in stripped and "IP Address" in stripped:
            in_data_section = True
            continue
        
        # Skip separator lines
        if "----" in stripped or "====" in stripped:
            continue
        
        # Parse interface data
        if in_data_section and stripped:
            # Typical format: Interface IP Address Physical Protocol VPN
            parts = stripped.split()
            if len(parts) >= 4:
                interfaces.append({
                    "interface": parts[0],
                    "ip_address": parts[1] if parts[1] != "unassigned" else None,
                    "physical": parts[2],
                    "protocol": parts[3],
                    "vpn": parts[4] if len(parts) > 4 else None,
                })
    
    return interfaces


async def show_interfaces_async(
    device_name: str,
    topology_path: Optional[Path],
    interface_filter: Optional[str],
    output_format: str,
    timeout: float = 10.0,
) -> int:
    """Async implementation of show-interfaces command.
    
    Args:
        device_name: Name of the device to connect to.
        topology_path: Optional path to topology file.
        interface_filter: Optional specific interface to show.
        output_format: Output format (text or json).
        timeout: Timeout in seconds for command execution.
        
    Returns:
        Exit code.
    """
    try:
        # Find and parse topology
        topo_file = find_topology_file(topology_path)
        topology = parse_topology(topo_file)
        
        # Find device
        device = get_device_or_none(topology, device_name, output_format)
        if device is None:
            return 1
        
        # Determine command based on filter
        if interface_filter:
            command = f"display ip interface {interface_filter}"
        else:
            command = "display ip interface brief"
        
        # Execute command
        output = await execute_show_command(device, command, timeout)
        
        # Parse interfaces
        interfaces = parse_interface_brief_output(output)
        
        # Filter if specific interface requested
        if interface_filter and not interface_filter.lower().startswith("display"):
            interfaces = [i for i in interfaces if interface_filter.lower() in i["interface"].lower()]
        
        # Output result
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "success",
                "device": device_name,
                "interfaces": interfaces,
            }))
        else:
            # Text output as table
            console.print(f"[cyan]Interface Status for {device_name}:[/cyan]")
            console.print("-" * 60)
            
            if not interfaces:
                console.print("[yellow]No interfaces found.[/yellow]")
            else:
                table = Table(
                    show_header=True,
                    header_style="bold magenta",
                )
                table.add_column("Interface", style="cyan")
                table.add_column("IP Address", style="green")
                table.add_column("Physical", style="blue")
                table.add_column("Protocol", style="yellow")
                
                for iface in interfaces:
                    ip_display = iface["ip_address"] if iface["ip_address"] else "unassigned"
                    physical_style = "green" if iface["physical"] == "up" else "red"
                    protocol_style = "green" if iface["protocol"] == "up" else "red"
                    
                    table.add_row(
                        iface["interface"],
                        ip_display,
                        f"[{physical_style}]{iface['physical']}[/{physical_style}]",
                        f"[{protocol_style}]{iface['protocol']}[/{protocol_style}]",
                    )
                
                console.print(table)
                console.print(f"\nTotal: {len(interfaces)} interface(s)")
        
        return 0
        
    except FileNotFoundError as e:
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": str(e),
            }))
        else:
            console.print(f"[red]Error: {e}[/red]")
        return 2
    except ValueError as e:
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": str(e),
            }))
        else:
            console.print(f"[red]Error: {e}[/red]")
        return 1
    except TopologyParserError as e:
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": f"Failed to parse topology file: {e}",
            }))
        else:
            console.print(f"[red]Error: Failed to parse topology file: {e}[/red]")
        return 3
    except ConnectionError as e:
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": str(e),
            }))
        else:
            console.print(f"[red]Error: {e}[/red]")
        return 1
    except asyncio.TimeoutError:
        error_msg = f"Command timed out after {timeout} seconds"
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": error_msg,
            }))
        else:
            console.print(f"[red]Error: {error_msg}[/red]")
        return 5


@app.command(name="show-interfaces")
def show_interfaces_command(
    device: str = typer.Argument(..., help="Device name"),
    topo_file: Optional[Path] = typer.Option(
        None,
        "--topology",
        "-t",
        help="Path to topology file",
        exists=True,
        readable=True,
        dir_okay=False,
        resolve_path=True,
    ),
    interface: Optional[str] = typer.Option(
        None,
        "--interface",
        "-i",
        help="Specific interface to display",
    ),
    output: str = typer.Option(
        "text",
        "--output",
        "-o",
        help="Output format: text, json",
    ),
    timeout: float = typer.Option(
        10.0,
        "--timeout",
        help="Command timeout in seconds",
    ),
) -> None:
    """Display device interface status.
    
    Shows IP interface brief information including IP addresses,
    physical and protocol states.
    
    Examples:
        ensp-cli show-interfaces Router1
        ensp-cli show-interfaces Router1 --interface GigabitEthernet0/0/0
        ensp-cli show-interfaces Router1 --output json
    
    Exit codes:
        0: Success
        1: General error or device not found
        2: Topology file not found
        3: Parse error
        5: Command timeout
    """
    exit_code = asyncio.run(show_interfaces_async(device, topo_file, interface, output, timeout))
    raise typer.Exit(exit_code)


def parse_routing_table_output(output: str) -> list[dict]:
    """Parse 'display ip routing-table' output into structured data.
    
    Args:
        output: Raw command output.
        
    Returns:
        List of route dictionaries.
    """
    routes = []
    lines = output.splitlines()
    
    # Parse routing table data
    in_data_section = False
    for line in lines:
        stripped = line.strip()
        
        # Skip header lines
        if not stripped:
            continue
        if "Destination" in stripped and "Mask" in stripped:
            in_data_section = True
            continue
        if "----" in stripped or "====" in stripped:
            continue
        if "Route Flags" in stripped or "Routing Tables" in stripped:
            continue
        
        # Parse route data
        # Format: Destination/Mask Proto Pre Cost Flags NextHop Interface
        if in_data_section:
            parts = stripped.split()
            if len(parts) >= 5:
                # Try to parse route entry
                try:
                    dest_mask = parts[0]
                    proto = parts[1] if len(parts) > 1 else ""
                    pre = parts[2] if len(parts) > 2 else ""
                    cost = parts[3] if len(parts) > 3 else ""
                    flags = parts[4] if len(parts) > 4 else ""
                    
                    # NextHop and Interface might be in different positions
                    nexthop = ""
                    iface = ""
                    if len(parts) > 5:
                        # Check if parts[5] looks like an IP or interface
                        if "." in parts[5] or ":" in parts[5]:
                            nexthop = parts[5]
                            iface = parts[6] if len(parts) > 6 else ""
                        else:
                            iface = parts[5]
                    
                    routes.append({
                        "destination": dest_mask,
                        "protocol": proto,
                        "preference": pre,
                        "cost": cost,
                        "flags": flags,
                        "nexthop": nexthop,
                        "interface": iface,
                    })
                except IndexError:
                    continue
    
    return routes


async def show_routes_async(
    device_name: str,
    topology_path: Optional[Path],
    protocol_filter: Optional[str],
    output_format: str,
    timeout: float = 10.0,
) -> int:
    """Async implementation of show-routes command.
    
    Args:
        device_name: Name of the device to connect to.
        topology_path: Optional path to topology file.
        protocol_filter: Optional protocol to filter by.
        output_format: Output format (text or json).
        timeout: Timeout in seconds for command execution.
        
    Returns:
        Exit code.
    """
    try:
        # Find and parse topology
        topo_file = find_topology_file(topology_path)
        topology = parse_topology(topo_file)
        
        # Find device
        device = get_device_or_none(topology, device_name, output_format)
        if device is None:
            return 1
        
        # Build command with optional protocol filter
        if protocol_filter:
            command = f"display ip routing-table protocol {protocol_filter}"
        else:
            command = "display ip routing-table"
        
        # Execute command
        output = await execute_show_command(device, command, timeout)
        
        # Parse routes
        routes = parse_routing_table_output(output)
        
        # Output result
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "success",
                "device": device_name,
                "protocol_filter": protocol_filter,
                "routes": routes,
            }))
        else:
            # Text output as table
            title = f"Routing Table for {device_name}"
            if protocol_filter:
                title += f" (Protocol: {protocol_filter})"
            console.print(f"[cyan]{title}:[/cyan]")
            console.print("-" * 80)
            
            if not routes:
                console.print("[yellow]No routes found.[/yellow]")
            else:
                table = Table(
                    show_header=True,
                    header_style="bold magenta",
                )
                table.add_column("Destination", style="cyan")
                table.add_column("Protocol", style="green")
                table.add_column("Pre", justify="right", style="blue")
                table.add_column("Cost", justify="right", style="yellow")
                table.add_column("NextHop", style="magenta")
                table.add_column("Interface", style="white")
                
                for route in routes:
                    table.add_row(
                        route["destination"],
                        route["protocol"],
                        route["preference"],
                        route["cost"],
                        route["nexthop"] or "-",
                        route["interface"] or "-",
                    )
                
                console.print(table)
                console.print(f"\nTotal: {len(routes)} route(s)")
        
        return 0
        
    except FileNotFoundError as e:
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": str(e),
            }))
        else:
            console.print(f"[red]Error: {e}[/red]")
        return 2
    except ValueError as e:
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": str(e),
            }))
        else:
            console.print(f"[red]Error: {e}[/red]")
        return 1
    except TopologyParserError as e:
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": f"Failed to parse topology file: {e}",
            }))
        else:
            console.print(f"[red]Error: Failed to parse topology file: {e}[/red]")
        return 3
    except ConnectionError as e:
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": str(e),
            }))
        else:
            console.print(f"[red]Error: {e}[/red]")
        return 1
    except asyncio.TimeoutError:
        error_msg = f"Command timed out after {timeout} seconds"
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": error_msg,
            }))
        else:
            console.print(f"[red]Error: {error_msg}[/red]")
        return 5


@app.command(name="show-routes")
def show_routes_command(
    device: str = typer.Argument(..., help="Device name"),
    topo_file: Optional[Path] = typer.Option(
        None,
        "--topology",
        "-t",
        help="Path to topology file",
        exists=True,
        readable=True,
        dir_okay=False,
        resolve_path=True,
    ),
    protocol: Optional[str] = typer.Option(
        None,
        "--protocol",
        "-p",
        help="Filter by protocol (static, ospf, bgp, direct)",
    ),
    output: str = typer.Option(
        "text",
        "--output",
        "-o",
        help="Output format: text, json",
    ),
    timeout: float = typer.Option(
        10.0,
        "--timeout",
        help="Command timeout in seconds",
    ),
) -> None:
    """Display device routing table.
    
    Shows IP routing table information including destinations,
    protocols, preferences, costs, and next hops.
    
    Examples:
        ensp-cli show-routes Router1
        ensp-cli show-routes Router1 --protocol ospf
        ensp-cli show-routes Router1 --output json
    
    Exit codes:
        0: Success
        1: General error or device not found
        2: Topology file not found
        3: Parse error
        5: Command timeout
    """
    exit_code = asyncio.run(show_routes_async(device, topo_file, protocol, output, timeout))
    raise typer.Exit(exit_code)


# =============================================================================
# Export Configuration Commands
# =============================================================================

async def export_config_async(
    device_name: str,
    output_path: Path,
    topology_path: Optional[Path],
    fmt: str,
    timeout: float = 10.0,
) -> int:
    """Async implementation of export-config command.
    
    Args:
        device_name: Name of the device to export.
        output_path: Path where the configuration will be saved.
        topology_path: Optional path to topology file.
        fmt: Export format (txt, json, md).
        timeout: Timeout in seconds for command execution.
        
    Returns:
        Exit code:
            0 - Success
            1 - General error or device not found
            2 - File not found (topology file)
            3 - Parse error (invalid topology file)
            5 - Command timeout
    """
    try:
        # Find and parse topology
        topo_file = find_topology_file(topology_path)
        topology = parse_topology(topo_file)
        
        # Find device
        device = get_device_or_none(topology, device_name, "text")
        if device is None:
            return 1
        
        # Export configuration
        exporter = ConfigExporter(topology, topo_file)
        result = await exporter.export_device_config(device, output_path, fmt, timeout)
        
        # Print success message
        console.print(f"[green]✓ Exported configuration for {device_name}[/green]")
        console.print(f"  Output: [cyan]{output_path.resolve()}[/cyan]")
        console.print(f"  Format: [dim]{fmt}[/dim]")
        
        return 0
        
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        return 2
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1
    except TopologyParserError as e:
        console.print(f"[red]Error: Failed to parse topology file: {e}[/red]")
        return 3
    except ConnectionError as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1
    except asyncio.TimeoutError:
        error_msg = f"Command timed out after {timeout} seconds"
        console.print(f"[red]Error: {error_msg}[/red]")
        return 5


@app.command(name="export-config")
def export_config_command(
    device: str = typer.Argument(..., help="Device name"),
    output: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Output file path",
        dir_okay=False,
        resolve_path=True,
    ),
    topo_file: Optional[Path] = typer.Option(
        None,
        "--topology",
        "-t",
        help="Path to topology file",
        exists=True,
        readable=True,
        dir_okay=False,
        resolve_path=True,
    ),
    fmt: str = typer.Option(
        "txt",
        "--format",
        "-f",
        help="Export format: txt, json, md",
    ),
    timeout: float = typer.Option(
        10.0,
        "--timeout",
        help="Command timeout in seconds",
    ),
) -> None:
    """Export a single device configuration to file.
    
    Connects to the specified device via Telnet, retrieves the
    current configuration, and saves it to the specified output file.
    
    Supported formats:
        - txt: Plain text with metadata header
        - json: Structured JSON with metadata and configuration
        - md: Markdown with syntax highlighting
    
    Examples:
        ensp-cli export-config Router1 -o r1.cfg
        ensp-cli export-config Router1 -o r1.json -f json
        ensp-cli export-config Router1 -o configs/r1.md -f md -t mylab.topo
    
    Exit codes:
        0: Success
        1: General error or device not found
        2: Topology file not found
        3: Parse error
        5: Command timeout
    """
    from ensp_cli.services.config_exporter import ConfigExporter
    
    exit_code = asyncio.run(export_config_async(
        device, output, topo_file, fmt, timeout
    ))
    raise typer.Exit(exit_code)


async def export_all_async(
    output_dir: Path,
    topology_path: Optional[Path],
    fmt: str,
    timeout: float,
    parallel: bool,
) -> int:
    """Async implementation of export-all command.
    
    Args:
        output_dir: Directory where configurations will be saved.
        topology_path: Optional path to topology file.
        fmt: Export format (txt, json, md).
        timeout: Timeout in seconds for each device.
        parallel: If True, fetch configs in parallel.
        
    Returns:
        Exit code:
            0 - All exports succeeded
            1 - General error
            2 - File not found (topology file)
            3 - Parse error (invalid topology file)
    """
    try:
        # Find and parse topology
        topo_file = find_topology_file(topology_path)
        topology = parse_topology(topo_file)
        
        # Export all configurations
        from ensp_cli.services.config_exporter import export_all_configs
        
        results = await export_all_configs(
            topology, output_dir, topo_file, fmt, timeout, parallel
        )
        
        # Generate summary
        success_count = sum(1 for r in results if r.get("success", False))
        total_count = len(results)
        
        console.print()
        console.print(f"[bold]Export Summary:[/bold]")
        console.print(f"  Total devices: {total_count}")
        console.print(f"  Successful: [green]{success_count}[/green]")
        console.print(f"  Failed: [red]{total_count - success_count}[/red]")
        
        # Show failed devices
        failed = [r for r in results if not r.get("success", False)]
        if failed:
            console.print(f"\n[yellow]Failed exports:[/yellow]")
            for r in failed:
                console.print(f"  - {r['device']}: {r.get('error', 'Unknown error')}")
        
        if success_count == total_count:
            console.print(f"\n[green]✓ All configurations exported to {output_dir.resolve()}[/green]")
            return 0
        elif success_count > 0:
            console.print(f"\n[yellow]⚠ Partial export completed[/yellow]")
            return 1
        else:
            console.print(f"\n[red]✗ All exports failed[/red]")
            return 1
        
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        return 2
    except TopologyParserError as e:
        console.print(f"[red]Error: Failed to parse topology file: {e}[/red]")
        return 3
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


@app.command(name="export-all")
def export_all_command(
    output_dir: Path = typer.Argument(
        ...,
        help="Output directory",
        file_okay=False,
        resolve_path=True,
    ),
    topo_file: Optional[Path] = typer.Option(
        None,
        "--topology",
        "-t",
        help="Path to topology file",
        exists=True,
        readable=True,
        dir_okay=False,
        resolve_path=True,
    ),
    fmt: str = typer.Option(
        "txt",
        "--format",
        "-f",
        help="Export format: txt, json, md",
    ),
    parallel: bool = typer.Option(
        True,
        "--parallel/--sequential",
        help="Fetch configs in parallel",
    ),
    timeout: float = typer.Option(
        10.0,
        "--timeout",
        help="Command timeout in seconds per device",
    ),
) -> None:
    """Export all device configurations.
    
    Connects to all devices in the topology and exports their
    configurations to files in the specified directory.
    
    Files are named: {device_name}.{format}
    
    Examples:
        ensp-cli export-all ./backup/
        ensp-cli export-all ./backup/ -f json
        ensp-cli export-all ./backup/ -t mylab.topo --sequential
        ensp-cli export-all ./backup/ -f md --timeout 15
    
    Exit codes:
        0: All exports succeeded
        1: Partial success or general error
        2: Topology file not found
        3: Parse error
    """
    from ensp_cli.services.config_exporter import ConfigExporter
    
    exit_code = asyncio.run(export_all_async(
        output_dir, topo_file, fmt, timeout, parallel
    ))
    raise typer.Exit(exit_code)


# =============================================================================
# Import Configuration Commands
# =============================================================================

async def import_config_async(
    device_name: str,
    config_file: Path,
    topology_path: Optional[Path],
    dry_run: bool,
    sections: Optional[list[str]],
    force: bool,
    variables: dict[str, str],
    output_format: str,
    timeout: float,
) -> int:
    """Async implementation of import-config command.
    
    Args:
        device_name: Name of the device to import to.
        config_file: Path to configuration file.
        topology_path: Optional path to topology file.
        dry_run: Preview without executing.
        sections: Optional sections to import.
        force: Skip confirmation for dangerous commands.
        variables: Template variables for substitution.
        output_format: Output format (text or json).
        timeout: Command timeout in seconds.
    
    Returns:
        Exit code.
    """
    importer = ConfigImporter()
    
    try:
        # Find and parse topology
        topo_file = find_topology_file(topology_path)
        topology = parse_topology(topo_file)
        
        # Find device
        device = get_device_or_none(topology, device_name, output_format)
        if device is None:
            return 1
        
        # Parse config file
        try:
            commands = importer.parse_config_file(config_file, sections)
        except ConfigImportError as e:
            if output_format.lower() == "json":
                print(json.dumps({"status": "error", "error": str(e)}))
            else:
                console.print(f"[red]Error: {e}[/red]")
            return 1
        
        if not commands:
            if output_format.lower() == "json":
                print(json.dumps({
                    "status": "error",
                    "error": "No commands found in configuration file",
                }))
            else:
                console.print("[yellow]Warning: No commands found in configuration file[/yellow]")
            return 1
        
        # Substitute variables
        if variables:
            try:
                commands = importer.substitute_variables(commands, variables)
            except ConfigImportError as e:
                if output_format.lower() == "json":
                    print(json.dumps({"status": "error", "error": str(e)}))
                else:
                    console.print(f"[red]Error: {e}[/red]")
                return 1
        
        # Validate commands
        is_valid, warnings = importer.validate_commands(commands)
        
        if not is_valid and not force:
            if output_format.lower() == "json":
                print(json.dumps({
                    "status": "error",
                    "error": "Dangerous commands detected",
                    "warnings": warnings,
                }))
            else:
                console.print("[yellow]Warning: Dangerous commands detected:[/yellow]")
                for warning in warnings:
                    console.print(f"  - {warning}")
                console.print("\nUse --force to proceed anyway.")
            return 1
        
        if warnings and output_format.lower() != "json":
            console.print("[yellow]Warning: The following dangerous commands were detected:[/yellow]")
            for warning in warnings:
                console.print(f"  - {warning}")
        
        # Dry run mode
        if dry_run:
            if output_format.lower() == "json":
                print(json.dumps({
                    "status": "dry_run",
                    "device": device_name,
                    "command_count": len(commands),
                    "commands": commands,
                    "warnings": warnings,
                }))
            else:
                console.print(f"[cyan]Dry run - Commands that would be executed on {device_name}:[/cyan]")
                console.print("-" * 60)
                for i, cmd in enumerate(commands, 1):
                    console.print(f"  {i}. {cmd}")
                console.print("-" * 60)
                console.print(f"Total: {len(commands)} command(s)")
            return 0
        
        # Confirm execution if not forced
        if not force and output_format.lower() != "json":
            console.print(f"[cyan]About to execute {len(commands)} command(s) on {device_name}:[/cyan]")
            console.print("-" * 60)
            for i, cmd in enumerate(commands[:5], 1):
                console.print(f"  {i}. {cmd}")
            if len(commands) > 5:
                console.print(f"  ... and {len(commands) - 5} more")
            console.print("-" * 60)
            
            # Simple confirmation (in a real app, use typer.confirm)
            confirm = input("Proceed with import? [y/N]: ")
            if confirm.lower() not in ("y", "yes"):
                console.print("[yellow]Import cancelled.[/yellow]")
                return 0
        
        # Execute import
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task(f"Importing configuration to {device_name}...", total=None)
            result = await importer.import_to_device(
                device=device,
                commands=commands,
                dry_run=False,
                timeout=timeout,
                stop_on_error=True,
                save_config=True,
            )
        
        # Output result
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "success" if result.success else "partial",
                "device": device_name,
                "commands_executed": result.commands_executed,
                "commands_failed": result.commands_failed,
                "failed_commands": result.failed_commands,
                "rollback_commands": result.rollback_commands,
            }))
        else:
            if result.success:
                console.print(f"[green]Successfully imported configuration to {device_name}[/green]")
                console.print(f"Commands executed: {result.commands_executed}")
            else:
                console.print(f"[red]Import partially failed on {device_name}[/red]")
                console.print(f"Commands executed: {result.commands_executed}")
                console.print(f"Commands failed: {result.commands_failed}")
                
                if result.failed_commands:
                    console.print("\n[yellow]Failed commands:[/yellow]")
                    for fc in result.failed_commands:
                        console.print(f"  - {fc['command']}: {fc['error']}")
                
                if result.rollback_commands:
                    console.print("\n[cyan]Rollback commands (to undo changes):[/cyan]")
                    for cmd in result.rollback_commands:
                        console.print(f"  {cmd}")
        
        return 0 if result.success else 1
        
    except FileNotFoundError as e:
        if output_format.lower() == "json":
            print(json.dumps({"status": "error", "error": str(e)}))
        else:
            console.print(f"[red]Error: {e}[/red]")
        return 2
    except ValueError as e:
        if output_format.lower() == "json":
            print(json.dumps({"status": "error", "error": str(e)}))
        else:
            console.print(f"[red]Error: {e}[/red]")
        return 1
    except TopologyParserError as e:
        if output_format.lower() == "json":
            print(json.dumps({"status": "error", "error": f"Failed to parse topology file: {e}"}))
        else:
            console.print(f"[red]Error: Failed to parse topology file: {e}[/red]")
        return 3
    except ConnectionError as e:
        if output_format.lower() == "json":
            print(json.dumps({"status": "error", "error": str(e)}))
        else:
            console.print(f"[red]Error: {e}[/red]")
        return 1
    except asyncio.TimeoutError:
        error_msg = f"Command timed out after {timeout} seconds"
        if output_format.lower() == "json":
            print(json.dumps({"status": "error", "error": error_msg}))
        else:
            console.print(f"[red]Error: {error_msg}[/red]")
        return 5


@app.command(name="import-config")
def import_config_command(
    device: str = typer.Argument(..., help="Device name"),
    config_file: Path = typer.Argument(
        ...,
        help="Configuration file to import",
        exists=True,
        readable=True,
        dir_okay=False,
        resolve_path=True,
    ),
    topo_file: Optional[Path] = typer.Option(
        None,
        "--topology",
        "-t",
        help="Path to topology file",
        exists=True,
        readable=True,
        dir_okay=False,
        resolve_path=True,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Preview commands without executing",
    ),
    section: Optional[list[str]] = typer.Option(
        None,
        "--section",
        "-s",
        help="Import specific section only (can be specified multiple times)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation for dangerous commands",
    ),
    var: Optional[list[str]] = typer.Option(
        None,
        "--var",
        help="Template variable (format: name=value, can be specified multiple times)",
    ),
    output: str = typer.Option(
        "text",
        "--output",
        "-o",
        help="Output format: text, json",
    ),
    timeout: float = typer.Option(
        10.0,
        "--timeout",
        help="Command timeout in seconds",
    ),
) -> None:
    """Import configuration from file to device.
    
    Connects to the specified device and applies configuration commands
    from the provided file. Supports template variables and section filtering.
    
    Examples:
        ensp-cli import-config Router1 config.txt
        ensp-cli import-config Router1 config.txt --dry-run
        ensp-cli import-config Router1 config.txt --section interface
        ensp-cli import-config Router1 template.txt --var hostname=R1 --var ip=192.168.1.1
        ensp-cli import-config Router1 config.txt --force
    
    Exit codes:
        0: Success
        1: General error or device not found
        2: Topology file not found
        3: Parse error
        5: Command timeout
    """
    # Parse template variables
    variables = {}
    if var:
        for v in var:
            if "=" in v:
                name, value = v.split("=", 1)
                variables[name.strip()] = value.strip()
            else:
                console.print(f"[red]Error: Invalid variable format '{v}'. Use 'name=value'.[/red]")
                raise typer.Exit(1)
    
    exit_code = asyncio.run(import_config_async(
        device_name=device,
        config_file=config_file,
        topology_path=topo_file,
        dry_run=dry_run,
        sections=section,
        force=force,
        variables=variables,
        output_format=output,
        timeout=timeout,
    ))
    raise typer.Exit(exit_code)


async def import_all_async(
    config_dir: Path,
    topology_path: Optional[Path],
    dry_run: bool,
    parallel: bool,
    continue_on_error: bool,
    output_format: str,
    timeout: float,
) -> int:
    """Async implementation of import-all command.
    
    Args:
        config_dir: Directory containing config files.
        topology_path: Optional path to topology file.
        dry_run: Preview without executing.
        parallel: Import to devices in parallel.
        continue_on_error: Continue if one device fails.
        output_format: Output format (text or json).
        timeout: Command timeout in seconds.
    
    Returns:
        Exit code.
    """
    importer = ConfigImporter()
    
    try:
        # Find and parse topology
        topo_file = find_topology_file(topology_path)
        topology = parse_topology(topo_file)
        
        # Scan for config files
        config_files = {}
        for cfg_file in config_dir.glob("*.cfg"):
            device_name = cfg_file.stem  # filename without extension
            config_files[device_name] = cfg_file
        
        for cfg_file in config_dir.glob("*.txt"):
            device_name = cfg_file.stem
            if device_name not in config_files:
                config_files[device_name] = cfg_file
        
        if not config_files:
            if output_format.lower() == "json":
                print(json.dumps({
                    "status": "error",
                    "error": f"No config files found in {config_dir}",
                }))
            else:
                console.print(f"[red]Error: No config files found in {config_dir}[/red]")
            return 1
        
        # Match with devices in topology
        matched_devices = []
        unmatched_configs = []
        
        for device_name, cfg_file in config_files.items():
            device = topology.get_device(device_name)
            if device:
                matched_devices.append((device, cfg_file))
            else:
                unmatched_configs.append(device_name)
        
        if output_format.lower() != "json":
            console.print(f"[cyan]Found {len(config_files)} config file(s):[/cyan]")
            console.print(f"  Matched with topology: {len(matched_devices)}")
            console.print(f"  Unmatched: {len(unmatched_configs)}")
            
            if unmatched_configs:
                console.print(f"  [yellow]Unmatched configs: {', '.join(unmatched_configs)}[/yellow]")
        
        if not matched_devices:
            if output_format.lower() == "json":
                print(json.dumps({
                    "status": "error",
                    "error": "No config files matched devices in topology",
                }))
            else:
                console.print("[red]Error: No config files matched devices in topology[/red]")
            return 1
        
        # Dry run mode
        if dry_run:
            results = []
            for device, cfg_file in matched_devices:
                try:
                    commands = importer.parse_config_file(cfg_file)
                    results.append({
                        "device": device.name,
                        "config_file": str(cfg_file),
                        "command_count": len(commands),
                        "commands": commands,
                    })
                except ConfigImportError as e:
                    results.append({
                        "device": device.name,
                        "config_file": str(cfg_file),
                        "error": str(e),
                    })
            
            if output_format.lower() == "json":
                print(json.dumps({
                    "status": "dry_run",
                    "results": results,
                }))
            else:
                console.print("[cyan]Dry run - Import preview:[/cyan]")
                for r in results:
                    if "error" in r:
                        console.print(f"\n[red]{r['device']}: Error - {r['error']}[/red]")
                    else:
                        console.print(f"\n[cyan]{r['device']} ({r['config_file']}):[/cyan]")
                        console.print(f"  Commands: {r['command_count']}")
                        for i, cmd in enumerate(r['commands'][:3], 1):
                            console.print(f"    {i}. {cmd}")
                        if r['command_count'] > 3:
                            console.print(f"    ... and {r['command_count'] - 3} more")
            return 0
        
        # Import to devices
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            if parallel:
                # Import in parallel using asyncio.gather
                import_tasks = []
                for device, cfg_file in matched_devices:
                    task = progress.add_task(f"Importing to {device.name}...", total=None)
                    import_tasks.append(
                        _import_single_device(
                            importer, device, cfg_file, timeout, task, progress
                        )
                    )
                
                parallel_results = await asyncio.gather(
                    *import_tasks, 
                    return_exceptions=True
                )
                
                for (device, _), result in zip(matched_devices, parallel_results):
                    if isinstance(result, Exception):
                        results.append(ImportResult(
                            success=False,
                            device=device.name,
                            commands_executed=0,
                            commands_failed=0,
                            error_message=str(result),
                        ))
                    else:
                        results.append(result)
            else:
                # Import sequentially
                for device, cfg_file in matched_devices:
                    task = progress.add_task(f"Importing to {device.name}...", total=None)
                    
                    try:
                        commands = importer.parse_config_file(cfg_file)
                        result = await importer.import_to_device(
                            device=device,
                            commands=commands,
                            dry_run=False,
                            timeout=timeout,
                            stop_on_error=not continue_on_error,
                            save_config=True,
                        )
                        results.append(result)
                        progress.update(task, description=f"[green]✓ {device.name}[/green]")
                    except Exception as e:
                        results.append(ImportResult(
                            success=False,
                            device=device.name,
                            commands_executed=0,
                            commands_failed=0,
                            error_message=str(e),
                        ))
                        progress.update(task, description=f"[red]✗ {device.name}[/red]")
                        
                        if not continue_on_error:
                            break
        
        # Generate summary
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "success" if not failed else "partial",
                "summary": {
                    "total": len(results),
                    "successful": len(successful),
                    "failed": len(failed),
                },
                "results": [
                    {
                        "device": r.device,
                        "success": r.success,
                        "commands_executed": r.commands_executed,
                        "commands_failed": r.commands_failed,
                        "error": r.error_message,
                    }
                    for r in results
                ],
            }))
        else:
            console.print("\n" + "=" * 60)
            console.print("[bold cyan]Import Summary[/bold cyan]")
            console.print("=" * 60)
            
            # Success table
            if successful:
                success_table = Table(
                    title="[green]Successful Imports[/green]",
                    show_header=True,
                    header_style="bold green",
                )
                success_table.add_column("Device", style="cyan")
                success_table.add_column("Commands", justify="right")
                
                for r in successful:
                    success_table.add_row(r.device, str(r.commands_executed))
                
                console.print(success_table)
            
            # Failure table
            if failed:
                failure_table = Table(
                    title="[red]Failed Imports[/red]",
                    show_header=True,
                    header_style="bold red",
                )
                failure_table.add_column("Device", style="cyan")
                failure_table.add_column("Error", style="red")
                
                for r in failed:
                    error = r.error_message or "Unknown error"
                    if len(error) > 50:
                        error = error[:47] + "..."
                    failure_table.add_row(r.device, error)
                
                console.print(failure_table)
            
            console.print(f"\nTotal: {len(results)} | Success: {len(successful)} | Failed: {len(failed)}")
        
        return 0 if not failed else 1
        
    except FileNotFoundError as e:
        if output_format.lower() == "json":
            print(json.dumps({"status": "error", "error": str(e)}))
        else:
            console.print(f"[red]Error: {e}[/red]")
        return 2
    except TopologyParserError as e:
        if output_format.lower() == "json":
            print(json.dumps({"status": "error", "error": f"Failed to parse topology file: {e}"}))
        else:
            console.print(f"[red]Error: Failed to parse topology file: {e}[/red]")
        return 3


async def _import_single_device(
    importer: ConfigImporter,
    device: Device,
    cfg_file: Path,
    timeout: float,
    task_id,
    progress,
) -> ImportResult:
    """Helper to import config to a single device."""
    try:
        commands = importer.parse_config_file(cfg_file)
        result = await importer.import_to_device(
            device=device,
            commands=commands,
            dry_run=False,
            timeout=timeout,
            stop_on_error=True,
            save_config=True,
        )
        progress.update(task_id, description=f"[green]✓ {device.name}[/green]")
        return result
    except Exception as e:
        progress.update(task_id, description=f"[red]✗ {device.name}[/red]")
        return ImportResult(
            success=False,
            device=device.name,
            commands_executed=0,
            commands_failed=0,
            error_message=str(e),
        )


@app.command(name="import-all")
def import_all_command(
    config_dir: Path = typer.Argument(
        ...,
        help="Directory with config files (named {device}.cfg or {device}.txt)",
        exists=True,
        readable=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    topo_file: Optional[Path] = typer.Option(
        None,
        "--topology",
        "-t",
        help="Path to topology file",
        exists=True,
        readable=True,
        dir_okay=False,
        resolve_path=True,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Preview commands without executing",
    ),
    parallel: bool = typer.Option(
        False,
        "--parallel",
        "-p",
        help="Import to devices in parallel",
    ),
    continue_on_error: bool = typer.Option(
        True,
        "--continue-on-error/--stop-on-error",
        help="Continue if one device fails",
    ),
    output: str = typer.Option(
        "text",
        "--output",
        "-o",
        help="Output format: text, json",
    ),
    timeout: float = typer.Option(
        10.0,
        "--timeout",
        help="Command timeout in seconds",
    ),
) -> None:
    """Import configuration to multiple devices.
    
    Scans the specified directory for config files named {device}.cfg or
    {device}.txt and imports them to matching devices in the topology.
    
    Examples:
        ensp-cli import-all ./configs/
        ensp-cli import-all ./configs/ --dry-run
        ensp-cli import-all ./configs/ --parallel
        ensp-cli import-all ./configs/ --stop-on-error
    
    Exit codes:
        0: All imports successful
        1: One or more imports failed
        2: Topology file not found
        3: Parse error
    """
    exit_code = asyncio.run(import_all_async(
        config_dir=config_dir,
        topology_path=topo_file,
        dry_run=dry_run,
        parallel=parallel,
        continue_on_error=continue_on_error,
        output_format=output,
        timeout=timeout,
    ))
    raise typer.Exit(exit_code)
