---
wave: 1
depends_on: []
files_modified:
  - src/ensp_cli/commands/device.py
  - src/ensp_cli/cli/main.py
  - src/ensp_cli/parser/topology_parser.py
autonomous: true
---

# Plan: Add/Remove Device Commands

## Goal
Implement device addition and removal commands for topology modification.

## Context
Phase 4 builds on the existing topology parsing foundation. We need to:
1. Add devices to the Topology model
2. Remove devices and their connections
3. Persist changes back to XML

## Tasks

<task id="1" name="Create device command module">
Create `src/ensp_cli/commands/device.py` with device management commands.

Implementation:
1. Import necessary modules (typer, pathlib, models)
2. Create `add_device_command()` Typer command
3. Create `remove_device_command()` Typer command
4. Implement device validation logic

<verify>
Module created with both command functions defined.
</verify>
</task>

<task id="2" name="Implement add-device command">
Add device to topology with validation.

Command signature:
```python
@app.command(name="add-device")
def add_device_command(
    name: str = typer.Argument(..., help="Device name"),
    device_type: str = typer.Option("Router", "--type", "-t", help="Device type"),
    model: str = typer.Option("AR2220", "--model", "-m", help="Device model"),
    console_port: int = typer.Option(0, "--port", "-p", help="Console port (0=auto)"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t"),
)
```

Implementation:
1. Load topology from file
2. Check for duplicate device names
3. Auto-assign console port if 0
4. Create Device model instance
5. Add to topology
6. Save topology back to file
7. Print success message

<verify>
Running `ensp-cli add-device TestRouter --type Router` adds device to topology.
</verify>
</task>

<task id="3" name="Implement remove-device command">
Remove device from topology with confirmation.

Command signature:
```python
@app.command(name="remove-device")
def remove_device_command(
    name: str = typer.Argument(..., help="Device name to remove"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
)
```

Implementation:
1. Load topology from file
2. Find device by name
3. If not force, prompt for confirmation
4. Remove device from topology
5. Remove all related connections
6. Save topology back to file
7. Print success message

<verify>
Running `ensp-cli remove-device TestRouter --force` removes device and connections.
</verify>
</task>

<task id="4" name="Register commands in main CLI">
Add device commands to main CLI.

Changes in `src/ensp_cli/cli/main.py`:
1. Import device commands
2. Register: `app.command(name="add-device")(add_device_command)`
3. Register: `app.command(name="remove-device")(remove_device_command)`

<verify>
Commands appear in `ensp-cli --help` output.
</verify>
</task>

<task id="5" name="Add tests for device commands">
Create tests in `tests/commands/test_device.py`.

Tests to add:
1. Test add-device creates device
2. Test add-device rejects duplicate names
3. Test remove-device removes device
4. Test remove-device removes connections
5. Test remove-device with --force skips confirmation

<verify>
All device command tests pass.
</verify>
</task>

## must_haves

Goal: User can add and remove devices from topology

- [ ] `ensp-cli add-device <name> --type <type>` creates new device
- [ ] Duplicate device names are rejected
- [ ] `ensp-cli remove-device <name>` removes device and connections
- [ ] Confirmation prompt unless --force used
- [ ] Changes saved to .topo file
- [ ] Tests cover add/remove functionality
