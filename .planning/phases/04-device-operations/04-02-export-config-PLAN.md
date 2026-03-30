---
wave: 1
depends_on: ["04-01-show-config-PLAN.md"]
files_modified:
  - src/ensp_cli/commands/config.py
  - src/ensp_cli/services/config_exporter.py
autonomous: true
---

# Plan: Export Device Configuration

## Goal
Implement configuration export to files for backup and sharing.

## Context
Users need to save device configurations for:
1. Backup before making changes
2. Sharing lab configurations
3. Version control of network configs
4. Documentation generation

## Tasks

<task id="1" name="Create config exporter service">
Create `src/ensp_cli/services/config_exporter.py`.

Implementation:
1. Define `ConfigExporter` class
2. Add `export_device_config(device, output_path)` method
3. Add `export_all_configs(topology, output_dir)` method
4. Support multiple formats: txt, json, markdown

<verify>
Service module created with exporter class.
</verify>
</task>

<task id="2" name="Implement export-config command">
Export single device configuration to file.

Command signature:
```python
@app.command(name="export-config")
def export_config_command(
    device: str = typer.Argument(..., help="Device name"),
    output: Path = typer.Option(..., "--output", "-o", help="Output file path"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t"),
    format: str = typer.Option("txt", "--format", "-f", help="Export format: txt, json, md"),
)
```

Implementation:
1. Load topology and find device
2. Fetch configuration via Telnet
3. Format according to specified format
4. Write to output file
5. Print success message with file path

Formats:
- txt: Raw config text
- json: Structured with device info + config
- md: Markdown with syntax highlighting

<verify>
Running `ensp-cli export-config R1 -o r1.cfg` creates config file.
</verify>
</task>

<task id="3" name="Implement export-all command">
Export all device configurations.

Command signature:
```python
@app.command(name="export-all")
def export_all_command(
    output_dir: Path = typer.Argument(..., help="Output directory"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t"),
    format: str = typer.Option("txt", "--format", "-f", help="Export format"),
    parallel: bool = typer.Option(True, "--parallel/--sequential", help="Fetch configs in parallel"),
)
```

Implementation:
1. Create output directory if not exists
2. For each device in topology:
   - Fetch configuration
   - Write to `{output_dir}/{device_name}.cfg`
3. Show progress with Rich progress bar
4. Generate summary report

<verify>
Running `ensp-cli export-all ./backup/` exports all configs.
</verify>
</task>

<task id="4" name="Add timestamp and metadata">
Include export metadata in files.

Implementation:
1. Add timestamp to exports
2. Include topology file path
3. Include device model and type
4. For JSON format, include full metadata object

Example JSON output:
```json
{
  "metadata": {
    "exported_at": "2026-03-30T10:30:00",
    "topology": "lab.topo",
    "device": "R1",
    "model": "AR2220"
  },
  "configuration": "..."
}
```

<verify>
Exported files contain metadata headers.
</verify>
</task>

<task id="5" name="Add tests for export functionality">
Create tests in `tests/services/test_config_exporter.py`.

Tests to add:
1. Test export_device_config creates file
2. Test all export formats work
3. Test export_all creates multiple files
4. Test JSON format includes metadata
5. Test error handling for invalid paths

<verify>
All export tests pass.
</verify>
</task>

## must_haves

Goal: User can export device configurations to files

- [ ] `ensp-cli export-config <device> -o <file>` exports single config
- [ ] Multiple formats supported (txt, json, md)
- [ ] `ensp-cli export-all <dir>` exports all devices
- [ ] Metadata included in exports
- [ ] Tests cover export functionality
