---
wave: 1
depends_on: []
files_modified:
  - src/ensp_cli/commands/config.py
  - src/ensp_cli/cli/main.py
autonomous: true
---

# Plan: Show Device Configuration

## Goal
Implement command to display device running configuration via console.

## Context
Building on existing exec command, add a dedicated config viewer that:
1. Connects to device console
2. Runs `display current-configuration` 
3. Shows output with syntax highlighting

## Tasks

<task id="1" name="Create config command module">
Create `src/ensp_cli/commands/config.py` with config management commands.

Implementation:
1. Import necessary modules (typer, device session, exec)
2. Create `show_config_command()` Typer command
3. Add helper for common VRP show commands

<verify>
Module created with show_config_command function defined.
</verify>
</task>

<task id="2" name="Implement show-config command">
Display device running configuration.

Command signature:
```python
@app.command(name="show-config")
def show_config_command(
    device: str = typer.Argument(..., help="Device name"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t"),
    section: Optional[str] = typer.Option(None, "--section", "-s", help="Filter section (e.g., 'interface', 'ospf')"),
    output: str = typer.Option("text", "--output", "-o", help="Output format: text, json"),
)
```

Implementation:
1. Load topology and find device
2. Connect via Telnet using existing session
3. Execute `display current-configuration`
4. If section specified, filter output
5. Display with Rich syntax highlighting
6. Support JSON output for automation

<verify>
Running `ensp-cli show-config R1` displays device configuration.
</verify>
</task>

<task id="3" name="Implement show-interfaces command">
Display device interface status.

Command signature:
```python
@app.command(name="show-interfaces")
def show_interfaces_command(
    device: str = typer.Argument(..., help="Device name"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t"),
    interface: Optional[str] = typer.Option(None, "--interface", "-i", help="Specific interface"),
)
```

Implementation:
1. Execute `display ip interface brief` or `display interface`
2. Parse and format output as table
3. Show IP address, status, protocol state

<verify>
Running `ensp-cli show-interfaces R1` displays interface table.
</verify>
</task>

<task id="4" name="Implement show-routes command">
Display routing table.

Command signature:
```python
@app.command(name="show-routes")
def show_routes_command(
    device: str = typer.Argument(..., help="Device name"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t"),
    protocol: Optional[str] = typer.Option(None, "--protocol", "-p", help="Filter by protocol (static, ospf, bgp, direct)"),
)
```

Implementation:
1. Execute `display ip routing-table`
2. If protocol specified, add protocol filter
3. Format as Rich table

<verify>
Running `ensp-cli show-routes R1` displays routing table.
</verify>
</task>

<task id="5" name="Register commands in main CLI">
Add config commands to main CLI.

Changes in `src/ensp_cli/cli/main.py`:
1. Import config commands
2. Register: show-config, show-interfaces, show-routes

<verify>
Commands appear in `ensp-cli --help` output.
</verify>
</task>

<task id="6" name="Add tests for config commands">
Create tests in `tests/commands/test_config.py`.

Tests to add:
1. Test show-config executes command and returns output
2. Test show-interfaces parses table correctly
3. Test show-routes with protocol filter
4. Test JSON output format
5. Test error handling for unreachable device

<verify>
All config command tests pass.
</verify>
</task>

## must_haves

Goal: User can view device configuration and status

- [ ] `ensp-cli show-config <device>` displays running config
- [ ] `--section` filter works for common sections
- [ ] `ensp-cli show-interfaces <device>` displays interface status
- [ ] `ensp-cli show-routes <device>` displays routing table
- [ ] JSON output supported for all commands
- [ ] Tests cover all commands
