---
wave: 2
depends_on: ["04-01-show-config-PLAN.md", "04-02-export-config-PLAN.md"]
files_modified:
  - src/ensp_cli/commands/config.py
  - src/ensp_cli/services/config_importer.py
autonomous: true
---

# Plan: Import Device Configuration

## Goal
Implement configuration import from files to devices via console.

## Context
Users need to import configurations for:
1. Restoring from backup
2. Deploying standard templates
3. Replicating lab setups
4. Bulk configuration updates

## Tasks

<task id="1" name="Create config importer service">
Create `src/ensp_cli/services/config_importer.py`.

Implementation:
1. Define `ConfigImporter` class
2. Add `parse_config_file(file_path)` method - extract commands from config
3. Add `validate_commands(commands)` method - check for dangerous commands
4. Add `import_to_device(device, commands, dry_run=False)` method
5. Handle different config formats (raw text, JSON with metadata)

<verify>
Service module created with importer class.
</verify>
</task>

<task id="2" name="Implement import-config command">
Import configuration from file to device.

Command signature:
```python
@app.command(name="import-config")
def import_config_command(
    device: str = typer.Argument(..., help="Device name"),
    config_file: Path = typer.Argument(..., help="Configuration file to import"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Preview commands without executing"),
    section: Optional[str] = typer.Option(None, "--section", "-s", help="Import specific section only"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
)
```

Implementation:
1. Load topology and find device
2. Read configuration file
3. Parse commands (handle section filter if specified)
4. Validate commands (warn on system-critical commands)
5. If dry-run: print commands that would be executed
6. If not force: show command count and ask for confirmation
7. Connect to device via Telnet
8. Enter system-view mode
9. Execute commands one by one
10. Check for errors after each command
11. Exit system-view
12. Save configuration (write memory)
13. Print success/failure summary

<verify>
Running `ensp-cli import-config R1 config.txt` applies configuration.
</verify>
</task>

<task id="3" name="Implement import-all command">
Import configuration to multiple devices.

Command signature:
```python
@app.command(name="import-all")
def import_all_command(
    config_dir: Path = typer.Argument(..., help="Directory with config files (named {device}.cfg)"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d"),
    parallel: bool = typer.Option(False, "--parallel", "-p", help="Import to devices in parallel"),
    continue_on_error: bool = typer.Option(True, "--continue-on-error", help="Continue if one device fails"),
)
```

Implementation:
1. Scan config directory for `{device_name}.cfg` files
2. Match with devices in topology
3. For each matched device:
   - Load configuration
   - Import to device
   - Track success/failure
4. Show progress with Rich progress bar
5. Generate summary report (success/failure per device)

<verify>
Running `ensp-cli import-all ./configs/` imports to all matched devices.
</verify>
</task>

<task id="4" name="Add command validation">
Validate and warn on dangerous commands.

Implementation:
1. Define list of dangerous commands:
   - `reboot`, `reset saved-configuration`
   - `delete`, `format`, `undo` (context-dependent)
   - Password changes (if not intended)
2. Before import, scan commands for dangerous patterns
3. If found, show warning and require explicit --force
4. Allow whitelist via config file

<verify>
Import with dangerous commands shows warning and requires --force.
</verify>
</task>

<task id="5" name="Add section extraction">
Extract specific section from full configuration.

Implementation:
1. Parse configuration into sections:
   - `system` (sysname, clock, etc.)
   - `interface` (interface configurations)
   - `routing` (static routes, OSPF, BGP, etc.)
   - `acl` (access control lists)
   - `user` (local users, AAA)
2. When --section specified, extract only that section
3. Support multiple sections: `--section interface --section routing`

<verify>
`--section interface` imports only interface configurations.
</verify>
</task>

<task id="6" name="Add template variables">
Support variable substitution in templates.

Implementation:
1. Define template syntax: `{{variable_name}}`
2. Add `--var` option: `--var hostname=R1 --var ip=192.168.1.1`
3. Before importing, substitute variables in config file
4. Support default values in template: `{{hostname:Router}}`

Example template:
```
sysname {{hostname}}
interface GigabitEthernet0/0/1
 ip address {{ip}} {{mask:255.255.255.0}}
```

<verify>
Variables are substituted before import.
</verify>
</task>

<task id="7" name="Add rollback on failure">
Restore previous configuration if import fails.

Implementation:
1. Before import, fetch current configuration (backup)
2. During import, track which commands succeeded
3. On failure:
   - Stop executing new commands
   - Option: rollback to previous config (if possible)
   - Or: save failed state and report
4. Generate rollback script for manual recovery

<verify>
Failed import generates rollback instructions.
</verify>
</task>

<task id="8" name="Add tests for import functionality">
Create tests in `tests/services/test_config_importer.py`.

Tests to add:
1. Test parse_config_file extracts commands
2. Test validate_commands detects dangerous commands
3. Test import_config applies commands to device
4. Test dry-run mode doesn't modify device
5. Test section extraction works
6. Test variable substitution works
7. Test error handling on failed command

<verify>
All import tests pass.
</verify>
</task>

## must_haves

Goal: User can import configuration from files to devices

- [ ] `ensp-cli import-config <device> <file>` applies configuration
- [ ] `--dry-run` previews commands without executing
- [ ] Dangerous command detection with warning
- [ ] `--section` imports specific config sections
- [ ] `ensp-cli import-all <dir>` imports to multiple devices
- [ ] Template variable substitution works
- [ ] Tests cover import functionality
