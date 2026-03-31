---
wave: 1
depends_on: ["04-01-show-config-PLAN.md", "04-02-export-config-PLAN.md"]
files_modified:
  - src/ensp_cli/commands/config.py
  - src/ensp_cli/services/config_differ.py
autonomous: true
---

# Plan: Compare Device Configurations

## Goal
Implement configuration comparison between devices or config files.

## Context
Users need to compare configurations for:
1. Finding differences between similar devices
2. Validating configuration consistency
3. Checking drift from baseline
4. Troubleshooting connectivity issues

## Tasks

<task id="1" name="Create config differ service">
Create `src/ensp_cli/services/config_differ.py`.

Implementation:
1. Define `ConfigDiffer` class
2. Add `compare_configs(config1, config2)` method
3. Return structured diff with added/removed/changed lines
4. Support ignoring timestamps, hostnames, etc.

<verify>
Service module created with differ class.
</verify>
</task>

<task id="2" name="Implement diff-config command">
Compare two device configurations.

Command signature:
```python
@app.command(name="diff-config")
def diff_config_command(
    device1: str = typer.Argument(..., help="First device name"),
    device2: str = typer.Argument(..., help="Second device name"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t"),
    section: Optional[str] = typer.Option(None, "--section", "-s", help="Compare specific section only"),
    ignore: List[str] = typer.Option([], "--ignore", "-i", help="Patterns to ignore"),
    output: str = typer.Option("text", "--output", "-o", help="Output format: text, json, unified"),
)
```

Implementation:
1. Load topology and find both devices
2. Fetch configurations via Telnet
3. If section specified, extract that section from both
4. Run diff comparison
5. Display results with color coding (green=added, red=removed)
6. Support unified diff format

<verify>
Running `ensp-cli diff-config R1 R2` shows config differences.
</verify>
</task>

<task id="3" name="Implement diff-file command">
Compare device with saved config file.

Command signature:
```python
@app.command(name="diff-file")
def diff_file_command(
    device: str = typer.Argument(..., help="Device name"),
    file: Path = typer.Argument(..., help="Config file to compare against"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t"),
    section: Optional[str] = typer.Option(None, "--section", "-s"),
)
```

Implementation:
1. Fetch device configuration
2. Read file configuration
3. Run diff comparison
4. Show differences from baseline

<verify>
Running `ensp-cli diff-file R1 baseline.cfg` compares with baseline.
</verify>
</task>

<task id="4" name="Add topology-wide diff">
Compare all devices against each other.

Command signature:
```python
@app.command(name="audit-configs")
def audit_configs_command(
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t"),
    group_by: str = typer.Option("type", "--group-by", help="Group by: type, model"),
    threshold: float = typer.Option(0.9, "--threshold", help="Similarity threshold for warnings"),
)
```

Implementation:
1. Group devices by type (Routers, Switches, etc.)
2. For each group, compare all pairs
3. Report devices with significant differences
4. Show similarity score
5. Flag potential misconfigurations

Example output:
```
Router Group (3 devices):
  R1 <-> R2: 95% similar ✓
  R1 <-> R3: 87% similar ✓
  R2 <-> R3: 45% similar ⚠️  Significant difference detected!
```

<verify>
Running `ensp-cli audit-configs` finds config inconsistencies.
</verify>
</task>

<task id="5" name="Add smart comparison options">
Intelligent diff ignoring volatile fields.

Implementation:
1. Add `--smart-ignore` flag to skip:
   - Timestamps in configuration
   - System uptime
   - Hostname (if comparing different devices)
   - Interface statistics
2. Add section-specific comparison:
   - `--section interface` compares only interfaces
   - `--section routing` compares only routing config
   - `--section acl` compares only ACLs

<verify>
Smart ignore filters out volatile configuration lines.
</verify>
</task>

<task id="6" name="Add tests for diff functionality">
Create tests in `tests/services/test_config_differ.py`.

Tests to add:
1. Test compare_configs finds differences
2. Test section extraction works
3. Test smart ignore filters correctly
4. Test audit-configs groups correctly
5. Test JSON output format

<verify>
All diff tests pass.
</verify>
</task>

## must_haves

Goal: User can compare device configurations

- [x] `ensp-cli diff-config <dev1> <dev2>` shows differences
- [x] `ensp-cli diff-file <device> <file>` compares with baseline
- [x] Section filtering works for common sections
- [x] Smart ignore filters volatile fields
- [x] `ensp-cli audit-configs` finds inconsistencies
- [x] Tests cover diff functionality

## Completion Summary

All tasks completed successfully:

1. **Config Differ Service** (`src/ensp_cli/services/config_differ.py`)
   - `ConfigDiffer` class with comparison logic
   - `ConfigDiff` and `DiffLine` dataclasses
   - Section extraction for interface, ospf, bgp, acl, vlan, routing, snmp, ntp
   - Smart ignore for timestamps, uptime, hostname, statistics
   - Similarity score calculation
   - Unified diff generation
   - Audit functionality for topology-wide comparisons

2. **CLI Commands** (`src/ensp_cli/commands/config.py`)
   - `diff-config <device1> <device2>` - Compare two devices
   - `diff-file <device> <file>` - Compare device with saved config file
   - `audit-configs` - Topology-wide configuration audit
   - Options: `--section`, `--ignore`, `--smart-ignore`, `--output`

3. **Tests** (`tests/services/test_config_differ.py`)
   - 45 tests covering all functionality
   - Tests for DiffLine, ConfigDiff, ConfigDiffer
   - Tests for compare_configs() and diff_from_files() functions
   - Tests for section extraction patterns
   - Tests for ignore patterns
   - Tests for audit functionality
