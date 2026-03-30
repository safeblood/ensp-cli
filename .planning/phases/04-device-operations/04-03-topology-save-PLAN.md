---
wave: 1
depends_on: ["04-01-add-remove-device-PLAN.md", "04-02-connect-disconnect-PLAN.md"]
files_modified:
  - src/ensp_cli/parser/topology_parser.py
  - src/ensp_cli/models/topology.py
autonomous: true
---

# Plan: Topology Save/Backup

## Goal
Ensure topology changes are persisted safely with backup/rollback.

## Context
All modification commands need:
1. XML serialization to write .topo files
2. Backup before changes
3. Rollback on error
4. Validation of saved data

## Tasks

<task id="1" name="Implement topology serialization">
Add `to_xml()` method to Topology model.

Changes in `src/ensp_cli/models/topology.py`:
1. Add `to_xml()` method that generates XML string
2. Format should match eNSP XML structure
3. Include all devices with attributes
4. Include all connections

XML format:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<topo>
  <devices>
    <dev id="..." name="..." model="..." com_port="..." cx="..." cy="..."/>
  </devices>
  <lines>
    <line srcDeviceID="..." destDeviceID="...">
      <interfacePair .../>
    </line>
  </lines>
</topo>
```

<verify>
Topology can be serialized to valid XML matching eNSP format.
</verify>
</task>

<task id="2" name="Implement save_topology function">
Add save functionality in parser module.

Changes in `src/ensp_cli/parser/topology_parser.py`:
1. Add `save_topology(topology: Topology, path: Path)` function
2. Generate XML using topology.to_xml()
3. Write to file with UTF-8 encoding
4. Return True on success

<verify>
Running save_topology() creates valid .topo file.
</verify>
</task>

<task id="3" name="Implement backup mechanism">
Add automatic backup before modification.

Implementation:
1. Before saving, create backup file: `.topo.bak` or `.topo.YYYYMMDD_HHMMSS`
2. Only keep last N backups (e.g., 5)
3. Store backup in same directory

<verify>
Backup file created before each topology modification.
</verify>
</task>

<task id="4" name="Implement rollback on error">
Add error handling with rollback.

Implementation:
1. Wrap save operation in try/except
2. On error, restore from backup
3. Print error message
4. Return appropriate exit code

<verify>
Failed save restores original file from backup.
</verify>
</task>

<task id="5" name="Add validation after save">
Verify saved topology can be loaded.

Implementation:
1. After saving, immediately load the file
2. Validate structure matches original
3. Check device count and connection count
4. Log warning if validation fails

<verify>
Saved topology passes validation check.
</verify>
</task>

<task id="6" name="Add restore command (optional)">
Add command to restore from backup.

Command signature:
```python
@app.command(name="restore")
def restore_command(
    backup_file: Optional[Path] = typer.Option(None, "--backup", "-b", help="Specific backup file"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t"),
    list_backups: bool = typer.Option(False, "--list", "-l", help="List available backups"),
)
```

<verify>
Running `ensp-cli restore` restores from latest backup.
</verify>
</task>

<task id="7" name="Add tests for save/backup">
Create tests in `tests/test_topology_save.py`.

Tests to add:
1. Test topology.to_xml() generates valid XML
2. Test save_topology creates file
3. Test backup created before save
4. Test rollback on failed save
5. Test validation after save

<verify>
All save/backup tests pass.
</verify>
</task>

## must_haves

Goal: Changes are persisted safely with backup/rollback

- [ ] Topology can be serialized to XML
- [ ] Changes saved to .topo file
- [ ] Backup created before modification
- [ ] Rollback on save failure
- [ ] Validation of saved topology
- [ ] Tests cover save/backup functionality
