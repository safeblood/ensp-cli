---
wave: 2
depends_on:
  - 02-01-telnet-client-PLAN.md
  - 02-02-interactive-session-PLAN.md
files_modified:
  - src/ensp_cli/commands/console.py
  - src/ensp_cli/main.py
  - tests/test_console_command.py
  - tests/integration/test_console_flow.py
autonomous: true
---

# Plan: CLI Console Command Integration

## Goal
Implement `ensp-cli console <device-name>` command that integrates the Telnet client and interactive session, with proper error handling and JSON output support.

## Tasks

<task id="1" name="Create console command module">
Create `src/ensp_cli/commands/console.py` with the console command implementation.

Command signature:
```python
@app.command(name="console")
def console_command(
    device_name: str = typer.Argument(..., help="Name of the device to connect to"),
    topology: Path | None = typer.Option(None, "--topology", "-t", help="Path to topology XML file"),
    output: str = typer.Option("text", "--output", "-o", help="Output format (text, json)"),
) -> None:
    """Open an interactive console session with a device."""
```

Implementation steps:
1. Load topology file (find .topo file in current directory if not specified)
2. Find device by name in topology
3. If not found, print error and exit with code 1
4. Establish Telnet connection via ConnectionManager
5. Start InteractiveSession
6. Handle KeyboardInterrupt for clean exit
7. Return exit code 0 on success, non-zero on failure

<verify>
- Command registered in main CLI
- Help text displayed with `ensp-cli console --help`
- Command accepts device_name argument
</verify>
</task>

<task id="2" name="Implement topology file discovery">
Add automatic topology file discovery when --topology not specified.

Implementation:
```python
def find_topology_file(path: Path | None = None) -> Path:
    """Find topology file in given path or current directory."""
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
        raise ValueError(f"Multiple .topo files found: {[f.name for f in topo_files]}. Use --topology to specify.")
    
    return topo_files[0]
```

<verify>
- Auto-discovers single .topo file in current directory
- Error when multiple .topo files exist
- Error when no .topo file found
- Respects explicit --topology path
</verify>
</task>

<task id="3" name="Add device lookup and error handling">
Implement device lookup with helpful error messages.

Implementation:
```python
def get_device_or_exit(topology: Topology, device_name: str) -> Device:
    """Find device or print error and exit."""
    device = next((d for d in topology.devices if d.name == device_name), None)
    if device is None:
        available = [d.name for d in topology.devices]
        print(f"Error: Device '{device_name}' not found in topology.", file=sys.stderr)
        print(f"Available devices: {', '.join(available)}", file=sys.stderr)
        raise typer.Exit(1)
    return device
```

Error cases:
- Device not found: List available devices
- Topology file not found: Suggest checking path
- Topology parse error: Show parse error details

<verify>
- Error message lists available devices when device not found
- Exit code 1 on device not found
- Exit code 1 on topology file not found
</verify>
</task>

<task id="4" name="Implement async entry point">
Create async wrapper for the console command.

Implementation:
```python
async def console_async(
    device_name: str,
    topology_path: Path | None,
    output_format: str,
) -> int:
    """Async implementation of console command."""
    try:
        # Find and parse topology
        topo_file = find_topology_file(topology_path)
        topology = parse_topology(topo_file)
        
        # Find device
        device = get_device_or_exit(topology, device_name)
        
        # Connect and start interactive session
        async with device_session(device) as client:
            if output_format == "json":
                print(json.dumps({
                    "status": "connected",
                    "device": device.name,
                    "address": f"127.0.0.1:{device.com_port}"
                }))
            else:
                print(f"Connected to {device.name} at 127.0.0.1:{device.com_port}")
                print("Press Ctrl+] or Ctrl+D to exit")
                print("-" * 40)
            
            session = InteractiveSession(client)
            await session.start()
            
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ConnectionError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nDisconnected.")
        return 0
```

<verify>
- Async function properly awaited
- Exceptions caught and converted to exit codes
- KeyboardInterrupt handled gracefully
</verify>
</task>

<task id="5" name="Add JSON output support">
Implement --output json flag for console command.

JSON output format:
```json
{
  "status": "connected",
  "device": "Router1",
  "address": "127.0.0.1:2000",
  "device_type": "Router",
  "platform": "AR2220"
}
```

Error JSON format:
```json
{
  "status": "error",
  "error": "Device not found",
  "device": "UnknownDevice",
  "available_devices": ["Router1", "Router2"]
}
```

Note: When in interactive mode, JSON output is only for initial connection status. The interactive session uses text output.

<verify>
- JSON output valid for connection status
- JSON output valid for errors
- Text mode still works as default
</verify>
</task>

<task id="6" name="Write tests">
Create comprehensive tests for console command.

Test files:
- `tests/test_console_command.py`: Unit tests with mocked Telnet
- `tests/integration/test_console_flow.py`: Integration tests

Test coverage:
- Device found → connection attempted
- Device not found → error + exit code 1
- Topology auto-discovery
- Explicit topology path
- Connection error handling
- JSON output format
- Exit codes (0=success, 1=failure)

<verify>
- All tests pass with `pytest tests/test_console_command.py -v`
- Integration tests pass (may require mocking)
- Exit codes verified in tests
</verify>
</task>

## must_haves

Goal: Implement `ensp-cli console <device-name>` command with proper integration

- [ ] `ensp-cli console <device-name>` command registered
- [ ] Topology file auto-discovery works
- [ ] Device lookup with helpful error messages
- [ ] Async entry point with proper exception handling
- [ ] --output json flag supported
- [ ] Exit codes: 0=success, 1=failure
- [ ] Ctrl+C / Ctrl+D exit handling
- [ ] Connection error messages are actionable
