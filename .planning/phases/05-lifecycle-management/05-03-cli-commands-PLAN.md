---
wave: 3
depends_on: ["05-01-device-launcher-PLAN.md", "05-02-process-manager-PLAN.md"]
files_modified:
  - src/ensp_cli/commands/lifecycle.py
  - src/ensp_cli/cli/main.py
autonomous: true
---

# Plan: CLI Commands

## Goal
Add launch, stop, and status commands to the CLI.

## Context
Building on launcher and process manager services to provide user-facing commands.

## Tasks

<task id="1" name="Create lifecycle command module">
Create `src/ensp_cli/commands/lifecycle.py`.

Implementation:
1. Import Typer, services
2. Create `app = typer.Typer()`
3. Import helper functions from console
4. Set up Rich console

<verify>
Module structure ready for commands.
</verify>
</task>

<task id="2" name="Implement launch-router command">
Add router launch command.

Command:
```python
@app.command(name="launch-router")
def launch_router_command(
    name: str = typer.Argument(..., help="Device name"),
    model: str = typer.Option("AR2220", "--model", "-m", help="Router model (AR2220, AR3260)"),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Console port (auto if not specified)"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t"),
    timeout: int = typer.Option(30, "--timeout", help="Seconds to wait for device ready"),
    update_topo: bool = typer.Option(True, "--update-topo/--no-update-topo", help="Update topology file"),
    x: Optional[int] = typer.Option(None, "--x", help="X coordinate in topology (auto if not specified)"),
    y: Optional[int] = typer.Option(None, "--y", help="Y coordinate in topology (auto if not specified)"),
)
```

Implementation:
1. Check if device name already running (global check)
2. Get port (auto-allocate if not specified)
3. **Detect GUI devices**: Scan for existing eNSP processes to avoid conflicts
4. **Calculate position**: If --x/--y not specified, auto-calculate to avoid overlap
5. Launch router via DeviceLauncher (with auto-retry)
6. Wait for readiness
7. Register with ProcessManager
8. **Update topology file**: Add device to .topo with console_port and coordinates
   - Backup original .topo file
   - Add `<dev>` node with `com_port`, `cx`, `cy`, and `source="cli"`
9. Display success message with port and position info

Output:
```
[OK] Launched router R1 (AR2220)
     Console: telnet 127.0.0.1:2000
     MAC: 54-89-98-XX-XX-XX
     PID: 12345
     Position: (500, 300)
     Topology updated: lab.topo
```

<verify>
Command launches router and updates topology file with coordinates.
</verify>
</task>

<task id="3" name="Implement launch-switch command">
Add switch launch command.

Command:
```python
@app.command(name="launch-switch")
def launch_switch_command(
    name: str = typer.Argument(..., help="Device name"),
    model: str = typer.Option("S5700", "--model", "-m", help="Switch model (S3700, S5700)"),
    port: Optional[int] = typer.Option(None, "--port", "-p"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t"),
    timeout: int = typer.Option(30, "--timeout"),
    update_topo: bool = typer.Option(True, "--update-topo/--no-update-topo"),
    x: Optional[int] = typer.Option(None, "--x", help="X coordinate in topology (auto if not specified)"),
    y: Optional[int] = typer.Option(None, "--y", help="Y coordinate in topology (auto if not specified)"),
)
```

Similar to launch-router but for switches. Includes GUI detection, topology update with coordinates.

Output:
```
[OK] Launched switch S1 (S5700)
     Console: telnet 127.0.0.1:2001
     MAC: 4C-1F-CC-XX-XX-XX
     PID: 12346
     Position: (600, 300)
     Topology updated: lab.topo
```

<verify>
Command launches switch and updates topology file with coordinates.
</verify>
</task>

<task id="4" name="Implement stop-device command">
Add device stop command.

Command:
```python
@app.command(name="stop-device")
def stop_device_command(
    name: str = typer.Argument(..., help="Device name to stop"),
    force: bool = typer.Option(False, "--force", "-f", help="Force kill if graceful stop fails"),
    all_devices: bool = typer.Option(False, "--all", "-a", help="Stop all running devices"),
)
```

Implementation:
1. Find device in ProcessManager
2. Attempt graceful stop
3. If fails and force=True, force kill
4. Unregister from ProcessManager
5. Display result

<verify>
Command stops devices correctly.
</verify>
</task>

<task id="5" name="Implement ps command">
Add list running devices command.

Command:
```python
@app.command(name="ps")
def ps_command(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table, json"),
    refresh: bool = typer.Option(True, "--refresh/--no-refresh", help="Refresh status before display"),
)
```

Output (table):
```
NAME    TYPE    MODEL    PORT   STATUS    UPTIME
R1      router  AR2220   2000   running   00:15:32
S1      switch  S5700    2001   running   00:10:15
```

<verify>
Command lists devices correctly.
</verify>
</task>

<task id="6" name="Implement launch-topology command">
Add batch topology launch command.

Command:
```python
@app.command(name="launch-topology")
def launch_topology_command(
    topo_file: Optional[Path] = typer.Argument(None, help="Topology file (auto-discover if not specified)"),
    timeout: int = typer.Option(60, "--timeout", help="Timeout per device"),
    parallel: bool = typer.Option(True, "--parallel/--sequential", help="Launch devices in parallel"),
)
```

Implementation:
1. Find topology file
2. Parse topology
3. For each device:
   - Determine type from device_type
   - Map to model (Router->AR2220, Switch->S5700)
   - Launch device
4. Show progress bar
5. Display summary

<verify>
Command launches all devices from topology.
</verify>
</task>

<task id="7" name="Register commands in CLI">
Update `src/ensp_cli/cli/main.py`.

Changes:
1. Import lifecycle commands
2. Register all commands:
   - launch-router
   - launch-switch
   - stop-device
   - ps
   - launch-topology

<verify>
All commands appear in help.
</verify>
</task>

## must_haves

Goal: All CLI commands work with good UX

- [ ] launch-router command works with GUI detection
- [ ] launch-switch command works with GUI detection
- [ ] Topology file updated with launched devices and **coordinates (cx, cy)**
- [ ] stop-device command works
- [ ] ps command shows running devices (both CLI and GUI)
- [ ] launch-topology works with progress bar
- [ ] Auto-retry on launch failure (3 times)
- [ ] All commands have help text and examples
- [ ] JSON output supported
- [ ] **Coordinate auto-allocation prevents device overlap in GUI**
- [ ] **Custom --x/--y parameters work for manual positioning**
