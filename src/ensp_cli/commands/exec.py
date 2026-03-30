"""Exec command for executing single commands on devices."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer

from ensp_cli.connection_manager import device_session
from ensp_cli.models import Device, Topology
from ensp_cli.parser.topology_parser import TopologyParser, TopologyParserError
from ensp_cli.telnet_client import VRP_PROMPT_ANY

# Import helper functions from console
from ensp_cli.commands.console import find_topology_file, get_device_or_exit, parse_topology


async def execute_command(
    device: Device,
    command: str,
    timeout: float = 10.0,
) -> str:
    """Execute a single command on a device and return the output.
    
    Args:
        device: The device to execute command on.
        command: The command to execute.
        timeout: Timeout in seconds for operations.
        
    Returns:
        Clean command output (without command echo or prompt).
        
    Raises:
        ConnectionError: If connection fails.
        asyncio.TimeoutError: If command times out.
    """
    async with device_session(device, timeout) as client:
        # Read initial banner/prompt
        await client.read_until(VRP_PROMPT_ANY, timeout=timeout)
        
        # Send command
        await client.write_line(command)
        
        # Read response until next prompt
        output = await client.read_until(VRP_PROMPT_ANY, timeout=timeout)
        
        # Strip command echo from beginning (first line)
        lines = output.splitlines()
        if lines and lines[0].strip() == command.strip():
            lines = lines[1:]
        
        # Strip trailing prompt (last line matching VRP pattern)
        if lines:
            last_line = lines[-1].strip()
            if VRP_PROMPT_ANY.search(last_line):
                lines = lines[:-1]
        
        # Join remaining lines
        clean_output = "\n".join(lines)
        
        return clean_output


async def exec_async(
    device_name: str,
    command: str,
    topology_path: Optional[Path],
    output_format: str,
    timeout: float = 10.0,
) -> int:
    """Async implementation of exec command.
    
    Args:
        device_name: Name of the device to connect to.
        command: Command to execute.
        topology_path: Optional path to topology file.
        output_format: Output format ("text" or "json").
        timeout: Timeout in seconds for command execution.
        
    Returns:
        Exit code:
            0 - Success
            1 - General error (device not found, connection failed, etc.)
            2 - File not found (topology file)
            3 - Parse error (invalid topology file)
            5 - Command timeout
    """
    try:
        # Find and parse topology
        topo_file = find_topology_file(topology_path)
        topology = parse_topology(topo_file)
        
        # Find device
        device = get_device_or_exit(topology, device_name, output_format)
        
        # Execute command
        output = await execute_command(device, command, timeout)
        
        # Output result
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "success",
                "device": device_name,
                "command": command,
                "output": output,
            }))
        else:
            # Text output - print clean output directly
            print(output)
        
        return 0
        
    except FileNotFoundError as e:
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": str(e),
            }))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": str(e),
            }))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1
    except TopologyParserError as e:
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": f"Failed to parse topology file: {e}",
            }))
        else:
            print(f"Error: Failed to parse topology file: {e}", file=sys.stderr)
        return 3
    except ConnectionError as e:
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": str(e),
            }))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1
    except asyncio.TimeoutError:
        error_msg = f"Command timed out after {timeout} seconds"
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "error",
                "error": error_msg,
            }))
        else:
            print(f"Error: {error_msg}", file=sys.stderr)
        return 5


def exec_command(
    device_name: str = typer.Argument(..., help="Name of the device"),
    command: str = typer.Argument(..., help='Command to execute (quoted, e.g., "display version")'),
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
    timeout: float = typer.Option(
        10.0,
        "--timeout",
        help="Command timeout in seconds",
    ),
    output: str = typer.Option(
        "text",
        "--output",
        "-o",
        help="Output format (text or json)",
    ),
) -> None:
    """Execute a single command on a device.
    
    Connects to the specified device via Telnet, executes the command,
    and returns the output. Command echo and prompts are automatically
    stripped from the output.
    
    Examples:
        ensp-cli exec Router1 "display version"
        ensp-cli exec Router1 "display ip interface brief" --output json
        ensp-cli exec Router1 "system-view" --topology mylab.topo
    """
    exit_code = asyncio.run(exec_async(device_name, command, topology, output, timeout))
    raise typer.Exit(exit_code)
