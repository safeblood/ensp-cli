---
wave: 2
depends_on: ["01-project-setup-models", "02-xml-parser"]
files_modified: []
autonomous: true
---

# Plan 03: CLI List Command with Output Formatting

## Goal
Implement Typer-based CLI with `list` command that displays topology devices in table format with JSON output support.

## Tasks

<task id="1" name="Set up Typer CLI structure">
Create main CLI entry point with Typer.

CLI structure:
- Entry point: `ensp-cli` command
- Main app with version flag (--version)
- Subcommand group for topology operations

Implementation:
- Use typer.Typer() as main app
- Version from package metadata
- Help text explaining tool purpose

<verify>
- `ensp-cli --version` prints version
- `ensp-cli --help` shows available commands
- Command returns exit code 0 on success
</verify>
</task>

<task id="2" name="Implement list command with table output">
Create `list` command that parses .topo file and displays device table.

Command: `ensp-cli list <topo-file>`

Features:
- Accept .topo file path as argument
- Parse using TopologyParser
- Display devices in Rich table format

Table columns:
- Name
- Type
- Model
- Console Port

Edge cases:
- Invalid file path → error message, exit code 1
- Empty topology → message indicating no devices

<verify>
- Command parses valid .topo file and displays table
- Table shows all devices with correct columns
- Invalid path shows error and returns exit code 1
</verify>
</task>

<task id="3" name="Add JSON output support">
Implement --output json flag for machine-readable output.

Command variants:
- `ensp-cli list <file>` → table output (default)
- `ensp-cli list <file> --output json` → JSON output
- `ensp-cli list <file> -o json` → shorthand

JSON structure:
```json
{
  "name": "topology-name",
  "devices": [...],
  "connections": [...]
}
```

<verify>
- JSON output is valid and parseable
- Contains all device and connection data
- Pydantic model serialization works correctly
</verify>
</task>

<task id="4" name="Implement connections view">
Add flag to show device connections instead of device list.

Command: `ensp-cli list <file> --show-connections`

Table columns for connections view:
- From Device
- From Port
- To Device
- To Port

<verify>
- --show-connections displays connections table
- Each connection shows all four fields
- Falls back to message if no connections exist
</verify>
</task>

<task id="5" name="Add comprehensive error handling">
Ensure all error cases have appropriate exit codes and messages.

Error scenarios:
- File not found → "Error: File not found: <path>", exit code 2
- Invalid XML → "Error: Failed to parse topology file: <details>", exit code 3
- Permission denied → "Error: Cannot read file: <path>", exit code 4
- Success → exit code 0

<verify>
- Each error scenario returns correct exit code
- Error messages are user-friendly
- Exit codes documented in help text
</verify>
</task>

<task id="6" name="Create CLI entry point">
Configure pyproject.toml with console script entry point.

Entry point:
```toml
[project.scripts]
ensp-cli = "ensp_cli.cli.main:app"
```

<verify>
- After `pip install -e .`, `ensp-cli` command is available
- Command runs without module path
</verify>
</task>

## must_haves

Goal: Implement Typer-based CLI with `list` command that displays topology devices

- [ ] `ensp-cli list <file>` displays devices in table format
- [ ] Table shows Name, Type, Model, and Console Port columns
- [ ] `--output json` produces valid JSON output
- [ ] `--show-connections` displays device-to-device links
- [ ] Invalid files produce clear error messages with non-zero exit code
- [ ] `ensp-cli --version` shows version
- [ ] CLI is installable via pip and available as `ensp-cli` command
