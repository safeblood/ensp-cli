# Phase 3: Command Execution & CLI Polish - Research

**Researched:** 2026-03-30
**Domain:** Typer CLI, Rich Terminal Formatting, Async Command Execution
**Confidence:** HIGH

## Summary

Phase 3 implements the `exec` command for non-interactive command execution on eNSP devices and completes CLI polish with proper exit codes, JSON output support, and Rich formatting. The foundation built in previous phases (Telnet client with `telnetlib3`, topology parsing, interactive console) provides the infrastructure needed for this phase.

The primary technical challenge is bridging the async telnet operations with Typer's synchronous CLI interface. Based on the existing codebase pattern (see `console.py`), the recommended approach is to create an async implementation function that handles the actual command execution, then wrap it with `asyncio.run()` in the Typer command function. This pattern cleanly separates async I/O from CLI argument handling.

For output formatting, Rich is already integrated and provides syntax highlighting via `rich.syntax.Syntax` with Pygments lexers. JSON output is straightforward using Python's `json` module with Rich's `print_json()` for pretty printing. Exit codes are handled via `typer.Exit(code=N)` which properly propagates to the shell.

**Primary recommendation:** Follow the established pattern in `console.py` - create an `exec_async()` function for the async logic, wrap it in a synchronous `exec_command()` Typer command, use Rich Console for formatted output, and raise `typer.Exit()` with appropriate codes.

## Standard Stack

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Typer | >=0.15.0 | CLI framework with type hints | Already integrated; provides automatic help generation, validation, and exit code handling |
| Rich | >=13.0.0 | Terminal formatting and syntax highlighting | Bundled with Typer; industry standard for Python CLI output |
| telnetlib3 | >=2.0 | Async Telnet client | Already integrated; async support essential for network I/O |
| Pygments | (via Rich) | Syntax highlighting for device output | Industry standard lexer library; supports 500+ languages/formats |

## Architecture Patterns

### Recommended Project Structure
```
src/ensp_cli/
├── cli/
│   └── main.py              # Main CLI app with command registration
├── commands/
│   ├── console.py           # Existing interactive console
│   └── exec.py              # NEW: Exec command implementation
├── telnet_client.py         # Reusable async Telnet client
└── ...
```

### Pattern 1: Async-to-Sync Bridge
**What:** Bridge async telnet operations with Typer's synchronous interface
**When to use:** Every command that needs async I/O (telnet operations)

```python
# commands/exec.py pattern
async def exec_async(device_name: str, command: str, ...) -> int:
    """Async implementation returns exit code."""
    async with device_session(device) as client:
        await client.write_line(command)
        output = await client.read_until_prompt()
        # ... handle output
    return 0  # success

@app.command()
def exec_command(
    device_name: str = typer.Argument(...),
    command: str = typer.Argument(...),
    ...
) -> None:
    """Sync wrapper that runs async implementation."""
    exit_code = asyncio.run(exec_async(device_name, command, ...))
    raise typer.Exit(exit_code)
```

### Pattern 2: Output Format Abstraction
**What:** Unified handling of text vs JSON output
**When to use:** All commands supporting `--output json`

```python
from enum import Enum

class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"

def output_result(data: dict, format: OutputFormat, console: Console):
    if format == OutputFormat.JSON:
        console.print_json(json.dumps(data))
    else:
        # Rich formatted text output
        console.print(...)
```

### Pattern 3: Error Handling with Exit Codes
**What:** Consistent error handling with proper shell exit codes
**When to use:** All error conditions in CLI commands

| Exit Code | Meaning | Usage |
|-----------|---------|-------|
| 0 | Success | Normal completion |
| 1 | General error | Connection failed, command failed |
| 2 | File not found | Topology file missing |
| 3 | Parse error | Invalid topology XML |
| 4 | Permission denied | Cannot read file |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Exit code propagation | `sys.exit()` in async code | `typer.Exit(code=N)` | Typer handles exception translation; works across async/sync boundary |
| Version flag | Custom `--version` handler | `typer.Option(callback=version_callback, is_eager=True)` | Standard pattern; handles edge cases like `--version --help` |
| Help documentation | Manual help text | Typer's automatic help generation | Derived from docstrings and type hints; always in sync |
| JSON pretty-print | `json.dumps(indent=2)` | `console.print_json()` or `Syntax(code, "json")` | Rich adds syntax highlighting; handles edge cases |
| Syntax highlighting | Custom regex highlighting | `rich.syntax.Syntax` with Pygments | 500+ lexers; proper parsing; theme support |
| Command output parsing | Manual string parsing | `TelnetClient.read_until(pattern)` with regex | Already implemented; handles buffering and timeouts |

## Common Pitfalls

### Pitfall 1: Async Context in Typer Commands
**What goes wrong:** Trying to use `await` directly in a Typer command function causes `SyntaxError`.

**How to avoid:** 
```python
# WRONG
@app.command()
async def exec(device: str):  # Typer doesn't support async commands
    await client.connect()

# CORRECT  
@app.command()
def exec(device: str):
    async def _impl():
        await client.connect()
    asyncio.run(_impl())
```

### Pitfall 2: Exit Code Not Propagating
**What goes wrong:** Using `return exit_code` in a Typer command doesn't set shell exit code.

**How to avoid:**
```python
# WRONG
@app.command()
def exec(device: str) -> int:
    return 1  # Shell sees exit code 0

# CORRECT
@app.command()
def exec(device: str) -> None:
    raise typer.Exit(1)  # Properly sets shell exit code
```

### Pitfall 3: Rich Output with JSON Mode
**What goes wrong:** Rich markup like `[red]error[/red]` appears literally in JSON output.

**How to avoid:**
```python
# Check format before applying Rich markup
if output_format == "json":
    print(json.dumps({"error": message}))  # Plain text
else:
    console.print(f"[red]{message}[/red]")  # Rich markup
```

### Pitfall 4: Command Echo in Output
**What goes wrong:** Device echoes the command back, and it appears in the output.

**How to avoid:**
```python
# Read and discard the echoed command line first
await client.write_line(command)
# Skip the echo line (device sends command back)
await client.read_until("\n")  # Or use prompt pattern
# Then read the actual output
output = await client.read_until_prompt()
```

### Pitfall 5: VRP Prompt Pattern Issues
**What goes wrong:** VRP has multiple prompt styles (`<hostname>`, `[hostname]`) and command-completion pauses.

**How to avoid:**
```python
# Use the existing VRP_PROMPT_ANY pattern from telnet_client.py
VRP_PROMPT_ANY = re.compile(r"(?:<[\w\-]+>|\[[\w\-]+(?:-[\w\/\-]+)*\])$", re.MULTILINE)

# Read until prompt, with timeout
output = await client.read_until(VRP_PROMPT_ANY, timeout=10.0)
```

## Code Examples

### Exec Command Implementation

```python
# commands/exec.py
import asyncio
import json
import re
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.syntax import Syntax

from ensp_cli.connection_manager import device_session
from ensp_cli.models import Device, Topology
from ensp_cli.parser.topology_parser import TopologyParser
from ensp_cli.telnet_client import VRP_PROMPT_ANY

console = Console()
app = typer.Typer()


async def exec_async(
    device_name: str,
    command: str,
    topology_path: Optional[Path],
    output_format: str,
) -> int:
    """Execute command on device and return exit code."""
    try:
        # Parse topology
        topo_file = find_topology_file(topology_path)
        topology = parse_topology(topo_file)
        device = get_device_or_exit(topology, device_name, output_format)
        
        async with device_session(device) as client:
            # Send command and read output
            await client.write_line(command)
            
            # Read until prompt (handles echo skipping internally)
            raw_output = await client.read_until(VRP_PROMPT_ANY, timeout=10.0)
            
            # Clean output (remove command echo and prompt)
            lines = raw_output.strip().split("\n")
            if lines and command in lines[0]:
                lines = lines[1:]  # Skip echo
            if lines and re.search(VRP_PROMPT_ANY, lines[-1]):
                lines = lines[:-1]  # Remove prompt line
            clean_output = "\n".join(lines).strip()
            
            # Output result
            if output_format == "json":
                result = {
                    "status": "success",
                    "device": device_name,
                    "command": command,
                    "output": clean_output,
                }
                console.print_json(json.dumps(result))
            else:
                # Syntax-highlighted output (use "cisco" or "ios" lexer if available)
                syntax = Syntax(clean_output, "text", theme="monokai")
                console.print(syntax)
            
            return 0
            
    except asyncio.TimeoutError:
        if output_format == "json":
            console.print_json(json.dumps({
                "status": "error",
                "error": "Command timed out",
            }))
        else:
            console.print("[red]Error: Command timed out[/red]", file=sys.stderr)
        return 1
    except ConnectionError as e:
        if output_format == "json":
            console.print_json(json.dumps({
                "status": "error",
                "error": str(e),
            }))
        else:
            console.print(f"[red]Error: {e}[/red]", file=sys.stderr)
        return 1


@app.command(name="exec")
def exec_command(
    device_name: str = typer.Argument(..., help="Device name from topology"),
    command: str = typer.Argument(..., help="Command to execute (quote if contains spaces)"),
    topology: Optional[Path] = typer.Option(
        None, "--topology", "-t", help="Path to topology file"
    ),
    output: str = typer.Option(
        "text", "--output", "-o", help="Output format (text, json)"
    ),
) -> None:
    """Execute a single command on a device and return the output.
    
    Examples:
        ensp-cli exec Router1 "display version"
        ensp-cli exec Switch1 "display vlan" --output json
        ensp-cli exec Router1 "display ip interface brief" -t lab.topo
    """
    exit_code = asyncio.run(exec_async(device_name, command, topology, output))
    raise typer.Exit(exit_code)
```

### Rich Syntax Highlighting for Network Output

```python
from rich.syntax import Syntax
from rich.console import Console

console = Console()

# For network device output, use "text" lexer if no specific lexer available
# Or try "cisco", "ios", "junos" if Pygments has them
output = """
interface GigabitEthernet0/0/1
 description Link to Core
 ip address 192.168.1.1 255.255.255.0
"""

# Basic text highlighting (no language-specific coloring)
syntax = Syntax(output, "text", theme="monokai", line_numbers=False)
console.print(syntax)

# For config-like output, you could use "ini" or "yaml" lexer for basic structure
syntax = Syntax(output, "ini", theme="monokai")
console.print(syntax)
```

### Exit Code Pattern

```python
import typer

# In main CLI, define exit codes in callback docstring
@app.callback()
def main():
    """CLI tool.
    
    Exit codes:
        0 - Success
        1 - General error (connection, command failed)
        2 - File not found
        3 - Parse error
    """
    pass

# In commands, raise typer.Exit with appropriate code
@app.command()
def exec(device: str) -> None:
    try:
        # ... execute command
        raise typer.Exit(0)
    except ConnectionError:
        console.print("[red]Connection failed[/red]", file=sys.stderr)
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]Topology not found[/red]", file=sys.stderr)
        raise typer.Exit(2)
```

### Version Flag Pattern (Already Implemented)

```python
# In cli/main.py - already implemented
def version_callback(value: bool) -> None:
    if value:
        console.print(f"ensp-cli version {__version__}")
        raise typer.Exit()

@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version", "-v",
        callback=version_callback,
        is_eager=True,  # Process before other options
        help="Show version and exit",
    ),
) -> None:
    pass
```

## Sources

### Primary (HIGH confidence)
- Typer Official Docs - Commands: https://typer.tiangolo.com/tutorial/commands/
- Typer Official Docs - Printing: https://typer.tiangolo.com/tutorial/printing/
- Typer Official Docs - Terminating/Exit: https://typer.tiangolo.com/tutorial/terminating/
- Typer Official Docs - Version Option: https://typer.tiangolo.com/tutorial/options/version/
- Rich Official Docs - Console: https://rich.readthedocs.io/en/latest/console.html
- Rich Official Docs - Syntax: https://rich.readthedocs.io/en/latest/syntax.html
- Pygments Lexers: https://pygments.org/docs/lexers/

### Secondary (MEDIUM confidence)
- telnetlib3 GitHub/ReadTheDocs (async patterns)
- Existing codebase: `src/ensp_cli/commands/console.py` - established async pattern
- Existing codebase: `src/ensp_cli/cli/main.py` - exit code and output format patterns
- Existing codebase: `src/ensp_cli/telnet_client.py` - VRP prompt patterns and async client
