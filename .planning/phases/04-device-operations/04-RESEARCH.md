# Phase 4: Device Operations - Research

**Researched:** 2026-03-30  
**Domain:** XML Serialization, File Backup, Topology Modification  
**Confidence:** HIGH

## Summary

Phase 4 requires implementing write-back functionality to .topo files, which involves:
1. Generating valid eNSP-compatible XML
2. Safe file operations with backup/rollback
3. Topology modification validation

All required functionality can be implemented using standard Python libraries plus existing project dependencies.

## Standard Stack

| Library | Purpose | Why Standard |
|---------|---------|--------------|
| xml.etree.ElementTree | XML generation | Python standard library, compatible with defusedxml |
| shutil | File backup/copy | Python standard library, battle-tested |
| pathlib | Path manipulation | Modern Python path handling |
| datetime | Backup timestamping | Standard library for timestamps |

## Architecture Patterns

### Pattern 1: Safe File Write with Backup
**What:** Write to temp file, backup original, then atomic move
**When to use:** All topology modifications

```python
import shutil
from pathlib import Path

def safe_write_topology(topology, path: Path) -> None:
    # Create backup
    backup_path = path.with_suffix(f".topo.bak")
    shutil.copy2(path, backup_path)
    
    # Write to temp file
    temp_path = path.with_suffix(".topo.tmp")
    temp_path.write_text(topology.to_xml(), encoding="utf-8")
    
    # Atomic replace
    temp_path.replace(path)
```

### Pattern 2: XML Generation with ElementTree
**What:** Build XML tree programmatically
**When to use:** Serializing topology to XML

```python
import xml.etree.ElementTree as ET

def topology_to_xml(topology: Topology) -> str:
    root = ET.Element("topo")
    devices_elem = ET.SubElement(root, "devices")
    
    for device in topology.devices:
        dev_elem = ET.SubElement(devices_elem, "dev")
        dev_elem.set("name", device.name)
        dev_elem.set("model", device.model)
        # ... more attributes
    
    return ET.tostring(root, encoding="unicode")
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XML generation | String concatenation | xml.etree.ElementTree | Prevents injection, ensures valid XML |
| File backup | Manual copy loops | shutil.copy2 | Preserves metadata, simpler |
| Atomic write | Direct overwrite | Write temp + replace | Prevents corruption on crash |

## Common Pitfalls

### Pitfall 1: XML Encoding Issues
**What goes wrong:** Non-ASCII characters in device names cause XML parsing errors.

**How to avoid:**
```python
# Always use UTF-8 encoding
xml_string = ET.tostring(root, encoding="unicode")
path.write_text(xml_string, encoding="utf-8")
```

### Pitfall 2: Backup Accumulation
**What goes wrong:** Unlimited backup files consume disk space.

**How to avoid:**
```python
def cleanup_old_backups(directory: Path, max_backups: int = 5):
    backups = sorted(directory.glob("*.topo.bak*"))
    for old_backup in backups[:-max_backups]:
        old_backup.unlink()
```

### Pitfall 3: Race Conditions
**What goes wrong:** Concurrent modifications corrupt file.

**How to avoid:** Use atomic file operations (temp file + rename).

## Code Examples

### Complete Save with Backup

```python
from pathlib import Path
import shutil
from datetime import datetime

def save_topology_with_backup(topology, path: Path) -> None:
    """Save topology with automatic backup."""
    # Generate timestamped backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.parent / f"{path.stem}_{timestamp}.topo.bak"
    
    # Backup existing file
    if path.exists():
        shutil.copy2(path, backup_path)
    
    # Write new content
    xml_content = topology.to_xml()
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(xml_content, encoding="utf-8")
    
    # Atomic replace
    temp_path.replace(path)
```

## Sources

- Python xml.etree.ElementTree docs: https://docs.python.org/3/library/xml.etree.elementtree.html
- shutil documentation: https://docs.python.org/3/library/shutil.html
- Pathlib documentation: https://docs.python.org/3/library/pathlib.html
