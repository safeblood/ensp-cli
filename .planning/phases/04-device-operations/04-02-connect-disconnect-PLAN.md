---
wave: 1
depends_on: ["04-01-add-remove-device-PLAN.md"]
files_modified:
  - src/ensp_cli/commands/device.py
  - src/ensp_cli/cli/main.py
autonomous: true
---

# Plan: Connect/Disconnect Commands

## Goal
Implement connection management between devices.

## Context
Building on device management, we need to:
1. Create connections between devices
2. Validate interface availability
3. Remove connections
4. Persist changes

## Tasks

<task id="1" name="Implement connect command">
Create connection between two devices.

Command signature:
```python
@app.command(name="connect")
def connect_command(
    device1: str = typer.Argument(..., help="First device name"),
    device2: str = typer.Argument(..., help="Second device name"),
    port1: str = typer.Option("GE0/0/0", "--port1", "-p1", help="Interface on device 1"),
    port2: str = typer.Option("GE0/0/0", "--port2", "-p2", help="Interface on device 2"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t"),
)
```

Implementation:
1. Load topology from file
2. Find both devices by name
3. Validate both devices exist
4. Check interface availability (not already used)
5. Create Connection model instance
6. Add to topology
7. Save topology back to file
8. Print success message with connection details

<verify>
Running `ensp-cli connect R1 R2 --port1 GE0/0/1 --port2 GE0/0/1` creates connection.
</verify>
</task>

<task id="2" name="Implement disconnect command">
Remove connection between devices.

Command signature:
```python
@app.command(name="disconnect")
def disconnect_command(
    device1: str = typer.Argument(..., help="First device name"),
    device2: str = typer.Argument(..., help="Second device name"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
)
```

Implementation:
1. Load topology from file
2. Find connection between devices
3. If not found, error
4. If not force, prompt for confirmation
5. Remove connection from topology
6. Save topology back to file
7. Print success message

<verify>
Running `ensp-cli disconnect R1 R2 --force` removes connection.
</verify>
</task>

<task id="3" name="Add interface validation">
Validate interface availability before connecting.

Implementation:
1. Check if port1 is already used on device1
2. Check if port2 is already used on device2
3. If conflict, print error with available interfaces
4. Suggest alternative interfaces

<verify>
Trying to use already-connected interface shows error.
</verify>
</task>

<task id="4" name="Add list-interfaces command (optional)">
Helper command to show available interfaces.

Command signature:
```python
@app.command(name="list-interfaces")
def list_interfaces_command(
    device_name: str = typer.Argument(..., help="Device name"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t"),
)
```

Implementation:
1. Load topology
2. Find device
3. Show all connections for device
4. List used and available interfaces

<verify>
Running `ensp-cli list-interfaces R1` shows interface status.
</verify>
</task>

<task id="5" name="Add tests for connect/disconnect">
Create tests in `tests/commands/test_device.py`.

Tests to add:
1. Test connect creates connection
2. Test connect validates device existence
3. Test connect detects interface conflicts
4. Test disconnect removes connection
5. Test disconnect validates connection exists

<verify>
All connect/disconnect tests pass.
</verify>
</task>

## must_haves

Goal: User can connect and disconnect devices

- [ ] `ensp-cli connect <dev1> <dev2>` creates connection
- [ ] Interface availability validation
- [ ] `ensp-cli disconnect <dev1> <dev2>` removes connection
- [ ] Changes saved to .topo file
- [ ] Tests cover connect/disconnect functionality
