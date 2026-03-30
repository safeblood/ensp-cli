"""Exec command for executing single commands on devices."""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ensp_cli.connection_manager import device_session
from ensp_cli.models import Device, Topology
from ensp_cli.parser.topology_parser import TopologyParser, TopologyParserError
from ensp_cli.telnet_client import VRP_PROMPT_ANY

# Import helper functions from console
from ensp_cli.commands.console import find_topology_file, get_device_or_none, parse_topology


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
        return await _execute_command_on_client(client, command, timeout)


async def _execute_command_on_client(
    client,
    command: str,
    timeout: float = 10.0,
) -> str:
    """Execute a command on an existing client connection.
    
    Internal helper used by both execute_command and execute_batch.
    
    Args:
        client: Connected Telnet client.
        command: The command to execute.
        timeout: Timeout in seconds for operations.
        
    Returns:
        Clean command output (without command echo or prompt).
    """
    # Wait for device to be ready and clear initial output
    await asyncio.sleep(0.3)
    await client.read_available()
    
    # Send command
    await client.write_line(command)
    
    # Wait for command to be echoed back (device echoes what we type)
    # Then read the actual output
    await asyncio.sleep(0.5)
    
    # Collect output until we see the prompt
    # Also handle "---- More ----" prompts by sending space
    start_time = asyncio.get_event_loop().time()
    all_output = ""
    
    while True:
        chunk = await client.read_available()
        if chunk:
            all_output += chunk
            
            # Check for "---- More ----" prompt and send space to continue
            if "---- More ----" in all_output:
                # Remove the More prompt from output
                all_output = all_output.replace("---- More ----", "")
                # Send space to continue output
                await client.write_line(" ")
                await asyncio.sleep(0.2)
                continue
            
            # Check for confirmation prompts (y/n) and auto-confirm
            if "(y/n)" in all_output.lower() or "Are you sure" in all_output:
                # Wait a moment for the full prompt to arrive
                await asyncio.sleep(0.3)
                # Send 'y' to confirm
                await client.write_line("y")
                await asyncio.sleep(0.3)
                continue
            
            # Check if we have the prompt (look at last few lines only)
            lines = all_output.replace('\r\n', '\n').split('\n')
            recent_lines = [line for line in lines[-3:] if line.strip()]
            if recent_lines:
                last_line = recent_lines[-1].strip()
                if VRP_PROMPT_ANY.search(last_line):
                    break
        
        # Check timeout
        if asyncio.get_event_loop().time() - start_time > timeout:
            raise asyncio.TimeoutError(f"Command timed out after {timeout} seconds")
        
        await asyncio.sleep(0.1)
    
    # Process output - handle both user view and system view prompts
    output = all_output.replace('\r\n', '\n')
    lines = output.splitlines()
    
    # Find and remove the command echo line
    # It may contain the prompt prefix like "[R2]display ..." or just "display ..."
    command_stripped = command.strip()
    first_content_line = 0
    for i, line in enumerate(lines):
        # Remove prompt prefix if present (both <R2> and [R2] formats)
        clean_line = line
        for pattern in [r'^[<\[][^\]>]+[>\]]\s*']:
            clean_line = re.sub(pattern, '', line)
        if command_stripped in clean_line or command_stripped in line:
            first_content_line = i + 1
            break
    
    lines = lines[first_content_line:]
    
    # Strip trailing prompt (last line matching VRP pattern)
    if lines:
        last_line = lines[-1].strip()
        if VRP_PROMPT_ANY.search(last_line):
            lines = lines[:-1]
    
    # Join remaining lines
    clean_output = "\n".join(lines)
    
    return clean_output


async def execute_batch(
    device: Device,
    commands: list[str],
    timeout: float = 10.0,
    stop_on_error: bool = True,
) -> list[dict]:
    """Execute multiple commands on a device in sequence.
    
    Args:
        device: The device to execute commands on.
        commands: List of commands to execute.
        timeout: Timeout in seconds for each command.
        stop_on_error: If True, stop execution on first error.
        
    Returns:
        List of result dictionaries with keys:
        - command: The command that was executed
        - output: Command output
        - success: Whether command succeeded
        - error: Error message if failed
    """
    results = []
    
    async with device_session(device, timeout) as client:
        for cmd in commands:
            cmd = cmd.strip()
            if not cmd:
                continue
                
            try:
                output = await _execute_command_on_client(client, cmd, timeout)
                results.append({
                    "command": cmd,
                    "output": output,
                    "success": True,
                    "error": None,
                })
            except Exception as e:
                results.append({
                    "command": cmd,
                    "output": "",
                    "success": False,
                    "error": str(e),
                })
                if stop_on_error:
                    break
    
    return results


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
        device = get_device_or_none(topology, device_name, output_format)
        if device is None:
            return 1
        
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


async def exec_batch_async(
    device_name: str,
    commands: list[str],
    topology_path: Optional[Path],
    output_format: str,
    timeout: float,
    stop_on_error: bool,
) -> int:
    """Async implementation of exec-batch command.
    
    Args:
        device_name: Name of the device to connect to.
        commands: List of commands to execute.
        topology_path: Optional path to topology file.
        output_format: Output format ("text" or "json").
        timeout: Timeout in seconds for each command.
        stop_on_error: Whether to stop on first error.
        
    Returns:
        Exit code:
            0 - All commands succeeded
            1 - General error (device not found, connection failed, etc.)
            2 - File not found (topology file)
            3 - Parse error (invalid topology file)
            5 - Command timeout or command failed
    """
    try:
        # Find and parse topology
        topo_file = find_topology_file(topology_path)
        topology = parse_topology(topo_file)
        
        # Find device
        device = get_device_or_none(topology, device_name, output_format)
        if device is None:
            return 1
        
        # Execute batch
        results = await execute_batch(device, commands, timeout, stop_on_error)
        
        # Output result
        if output_format.lower() == "json":
            print(json.dumps({
                "status": "success" if all(r["success"] for r in results) else "partial",
                "device": device_name,
                "results": results,
            }))
        else:
            # Text output
            console = Console()
            for i, result in enumerate(results, 1):
                console.print(f"\n[bold cyan]$ {result['command']}[/bold cyan]")
                if result["success"]:
                    if result["output"]:
                        console.print(result["output"])
                else:
                    console.print(f"[red]Error: {result['error']}[/red]")
        
        # Return 0 if all succeeded, 5 if any failed
        return 0 if all(r["success"] for r in results) else 5
        
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
    
    Exit codes:
        0: Success
        1: General error or device not found
        2: Topology file not found
        3: Parse error
        5: Command timeout
    """
    exit_code = asyncio.run(exec_async(device_name, command, topology, output, timeout))
    raise typer.Exit(exit_code)


def exec_batch_command(
    device_name: str = typer.Argument(..., help="Name of the device"),
    commands: list[str] = typer.Argument(..., help='Commands to execute (quoted, e.g., "system-view" "interface GE0/0/1")'),
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
    stop_on_error: bool = typer.Option(
        True,
        "--stop-on-error/--continue-on-error",
        help="Stop execution on first error",
    ),
) -> None:
    """Execute multiple commands on a device in sequence.
    
    Connects to the device once and executes all commands in order,
    maintaining the connection state between commands. This allows
    entering system view and configuring interfaces in one operation.
    
    Examples:
        ensp-cli exec-batch Router1 "system-view" "interface GE0/0/1" "ip address 192.168.1.1 24"
        ensp-cli exec-batch Router1 "display version" "display cpu" --output json
        ensp-cli exec-batch Router1 "system-view" "undo ospf" --continue-on-error
    
    Exit codes:
        0: All commands succeeded
        1: General error or device not found
        2: Topology file not found
        3: Parse error
        5: One or more commands failed (or timeout)
    """
    exit_code = asyncio.run(exec_batch_async(
        device_name, commands, topology, output, timeout, stop_on_error
    ))
    raise typer.Exit(exit_code)
