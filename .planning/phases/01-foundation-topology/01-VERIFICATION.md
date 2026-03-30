# Phase 1 Verification: Foundation & Topology Parsing

## Executive Summary

**Score:** 18/18 must_haves verified  
**Status:** PASSED ✓  
**Verified:** 2026-03-30  

All phase requirements have been successfully implemented and verified. The project has proper data models for Device, Connection, and Topology; a secure XML parser using defusedxml; and a functional CLI with table/JSON output and connections view.

---

## must_haves Verification

### Plan 01: Project Setup and Pydantic Models

#### must_have: Project can be installed with `pip install -e .`

**Status:** PASS ✓

**Evidence:**
- `pyproject.toml` exists with all required configuration (lines 1-76)
- Dependencies include: pydantic>=2.10.0, defusedxml>=0.7.1, typer>=0.15.0, rich>=13.0.0
- Entry point configured: `ensp-cli = "ensp_cli.cli.main:app"` (line 37)
- Installation completed successfully during test run
- Package imports work correctly (verified in all tests)

---

#### must_have: Device model validates name, type, model, and console port

**Status:** PASS ✓

**Evidence:**
- File: `src/ensp_cli/models/device.py`
- Lines 21-27: `validate_name()` ensures non-empty name
- Lines 29-35: `validate_device_type()` ensures non-empty type
- Lines 37-43: `validate_model()` ensures non-empty model  
- Lines 45-51: `validate_console_port()` ensures port is 1-65535

**Tests verified:** (tests/test_models.py)
- `test_device_empty_name_raises` - empty name raises ValidationError
- `test_device_whitespace_name_raises` - whitespace-only name raises ValidationError
- `test_device_empty_type_raises` - empty type raises ValidationError
- `test_device_empty_model_raises` - empty model raises ValidationError
- `test_device_invalid_console_port_zero` - port 0 raises ValidationError
- `test_device_invalid_console_port_negative` - negative port raises ValidationError
- `test_device_invalid_console_port_too_high` - port > 65535 raises ValidationError
- `test_device_valid_boundary_ports` - ports 1 and 65535 are valid

All 10 Device tests passing.

---

#### must_have: Connection model validates device-to-device links

**Status:** PASS ✓

**Evidence:**
- File: `src/ensp_cli/models/connection.py`
- Lines 21-26: `validate_devices_not_same()` prevents self-connections
- Lines 28-39: `validate_non_empty_fields()` ensures all fields non-empty
- Lines 52-61: `involves_device()` method for checking device involvement

**Tests verified:** (tests/test_models.py)
- `test_connection_same_device_raises` - same source/target raises ValidationError
- `test_connection_empty_from_port_raises` - empty from_port raises ValidationError
- `test_connection_empty_to_port_raises` - empty to_port raises ValidationError
- `test_connection_involves_device` - involves_device() works correctly

All 5 Connection tests passing.

---

#### must_have: Topology model aggregates devices and connections

**Status:** PASS ✓

**Evidence:**
- File: `src/ensp_cli/models/topology.py`
- Lines 25-26: `devices` and `connections` list fields
- Lines 38-40: `device_count` property
- Lines 42-45: `connection_count` property
- Lines 47-59: `get_device()` finds device by name
- Lines 61-73: `get_connections_for()` filters connections by device
- Lines 75-86: `add_device()` with duplicate detection
- Lines 88-101: `add_connection()` with device validation

**Tests verified:** (tests/test_models.py)
- `test_topology_get_device_found` - returns correct device
- `test_topology_get_device_not_found` - returns None
- `test_topology_get_connections_for` - filters correctly
- `test_topology_add_device` - adds device successfully
- `test_topology_add_device_duplicate_raises` - prevents duplicates
- `test_topology_add_connection` - adds connection successfully
- `test_topology_add_connection_missing_source_raises` - validates source device
- `test_topology_add_connection_missing_target_raises` - validates target device
- `test_topology_device_count_property` - returns correct count
- `test_topology_connection_count_property` - returns correct count

All 14 Topology tests passing.

---

#### must_have: All models have proper type hints and validation

**Status:** PASS ✓

**Evidence:**
- All model files use Python 3.10+ type hints (e.g., `list[Device]`, `Path | None`)
- Pydantic BaseModel with Field descriptions throughout
- mypy configuration in pyproject.toml (lines 53-59)
- All 29 model tests passing with validation verified

---

#### must_have: Models can be imported from ensp_cli.models

**Status:** PASS ✓

**Evidence:**
- File: `src/ensp_cli/models/__init__.py`
- Line 3-5: Exports Device, Connection, Topology
- Line 7: `__all__` properly defined
- All tests use: `from ensp_cli.models import Connection, Device, Topology` (works correctly)

---

### Plan 02: XML Topology Parser Implementation

#### must_have: Parser uses defusedxml for XXE protection

**Status:** PASS ✓

**Evidence:**
- File: `src/ensp_cli/parser/topology_parser.py`
- Line 5: `import defusedxml.ElementTree as ET` (using defusedxml, not stdlib xml.etree)
- Line 6: `from defusedxml.ElementTree import ParseError`
- Lines 48, 69: Uses `ET.fromstring()` for secure parsing

**Tests verified:** (tests/test_parser.py)
- `test_defusedxml_security_xxe` - XXE payload safely handled
- `test_defusedxml_security_billion_laughs` - XML bomb prevented

---

#### must_have: Parser correctly extracts all devices from .topo files

**Status:** PASS ✓

**Evidence:**
- File: `src/ensp_cli/parser/topology_parser.py`
- Lines 107-126: `_parse_devices()` iterates through `<dev>` elements
- Lines 128-170: `_parse_device()` extracts name, model, com_port attributes
- Lines 172-194: `_determine_device_type()` maps models to device types

**Tests verified:** (tests/test_parser.py)
- `test_parse_valid_sample_file` - extracts 3 devices from sample file (LSW2, Cloud1, R2)
- `test_parse_string_valid_xml` - extracts devices from XML string
- `test_parse_empty_topology` - handles empty device list
- `test_device_type_mapping` - correctly maps Router, Switch, Cloud, Firewall types

**Runtime verified:**
```
$ ensp-cli list "1.topo"
┌─────────────────────────────────────────┐
│ Devices in '1'                          │
├────────┬────────┬────────┬──────────────┤
│ Name   │ Type   │ Model  │ Console Port │
├────────┼────────┼────────┼──────────────┤
│ LSW2   │ Switch │ S5700  │         2001 │
│ Cloud1 │ Cloud  │ Cloud  │            1 │
│ R2     │ Router │ Router │         2000 │
└────────┴────────┴────────┴──────────────┘
```

---

#### must_have: Parser correctly extracts all connections from .topo files

**Status:** PASS ✓

**Evidence:**
- File: `src/ensp_cli/parser/topology_parser.py`
- Lines 196-215: `_parse_connections()` iterates through `<line>` elements
- Lines 217-241: `_parse_connection()` extracts from_device, from_port, to_device, to_port

**Tests verified:** (tests/test_parser.py)
- `test_parse_with_connections` - correctly parses connection with all fields
- Connection correctly extracted: R1:GE0/0/0 -> R2:GE0/0/0

---

#### must_have: Invalid/malformed files produce clear error messages

**Status:** PASS ✓

**Evidence:**
- File: `src/ensp_cli/parser/topology_parser.py`
- Lines 49-52: `TopologyParserError` raised for XML parse errors with clear message
- Lines 142-143: Clear error when device missing 'name' attribute
- Lines 146-147: Clear error when device missing 'model' attribute
- Lines 153-156: Clear error for invalid com_port value

**Tests verified:** (tests/test_parser.py)
- `test_parse_string_invalid_xml` - "Invalid XML" error message
- `test_parse_device_missing_name` - "missing required 'name' attribute"
- `test_parse_device_missing_model` - "missing required 'model' attribute"
- `test_parse_device_invalid_com_port` - "invalid com_port value"

---

#### must_have: File not found produces clear error message

**Status:** PASS ✓

**Evidence:**
- File: `src/ensp_cli/parser/topology_parser.py`
- Lines 38-39: Raises `FileNotFoundError` with message "Topology file not found: {path}"

**CLI handling:** (src/ensp_cli/cli/main.py)
- Lines 171-173: Catches FileNotFoundError, prints "Error: File not found: {path}", exits with code 2

**Runtime verified:**
```
$ ensp-cli list "nonexistent.topo"
Error: File not found: nonexistent.topo
Exit code: 2
```

---

#### must_have: Parser can be imported from ensp_cli.parser

**Status:** PASS ✓

**Evidence:**
- File: `src/ensp_cli/parser/__init__.py`
- Lines 3: `from ensp_cli.parser.topology_parser import TopologyParser, TopologyParserError`
- Line 5: `__all__` properly defined
- All parser tests use: `from ensp_cli.parser import TopologyParser, TopologyParserError` (works correctly)

---

### Plan 03: CLI List Command with Output Formatting

#### must_have: `ensp-cli list <file>` displays devices in table format

**Status:** PASS ✓

**Evidence:**
- File: `src/ensp_cli/cli/main.py`
- Lines 107-126: `_output_table()` creates Rich table with device data
- Lines 129-182: `list` command with topo_file argument
- Lines 164: Uses `TopologyParser().parse_file(topo_file)`

**Runtime verified:**
```
$ ensp-cli list "1.topo"
┌─────────────────────────────────────────┐
│ Devices in '1'                          │
├────────┬────────┬────────┬──────────────┤
│ Name   │ Type   │ Model  │ Console Port │
├────────┼────────┼────────┼──────────────┤
│ LSW2   │ Switch │ S5700  │         2001 │
│ Cloud1 │ Cloud  │ Cloud  │            1 │
│ R2     │ Router │ Router │         2000 │
└────────┴────────┴────────┴──────────────┘

Total: 3 device(s)
```

---

#### must_have: Table shows Name, Type, Model, and Console Port columns

**Status:** PASS ✓

**Evidence:**
- File: `src/ensp_cli/cli/main.py`
- Lines 112-115: Table columns defined:
  - `add_column("Name", style="cyan")`
  - `add_column("Type", style="green")`
  - `add_column("Model", style="blue")`
  - `add_column("Console Port", justify="right", style="yellow")`

**Runtime verified:** See table output above with all four columns present.

---

#### must_have: `--output json` produces valid JSON output

**Status:** PASS ✓

**Evidence:**
- File: `src/ensp_cli/cli/main.py`
- Lines 65-72: `_output_json()` function
- Lines 166-167: `--output json` triggers JSON output

**Runtime verified:**
```
$ ensp-cli list "1.topo" --output json
{
  "name": "1",
  "devices": [
    {"name": "LSW2", "device_type": "Switch", "model": "S5700", "console_port": 2001},
    {"name": "Cloud1", "device_type": "Cloud", "model": "Cloud", "console_port": 1},
    {"name": "R2", "device_type": "Router", "model": "Router", "console_port": 2000}
  ],
  "connections": []
}
```

---

#### must_have: `--show-connections` displays device-to-device links

**Status:** PASS ✓

**Evidence:**
- File: `src/ensp_cli/cli/main.py`
- Lines 77-101: Connection table output in `_output_table()`
- Lines 145-150: `--show-connections` option definition
- Lines 169: Passed to `_output_table()` function

**Runtime verified:**
```
$ ensp-cli list "1.topo" --show-connections
No connections found in topology.
```

---

#### must_have: Invalid files produce clear error messages with non-zero exit code

**Status:** PASS ✓

**Evidence:**
- File: `src/ensp_cli/cli/main.py`
- Lines 171-173: FileNotFoundError → exit code 2
- Lines 174-176: PermissionError → exit code 4
- Lines 177-179: TopologyParserError → exit code 3
- Lines 180-182: General errors → exit code 1

**Runtime verified:**
```
$ ensp-cli list "nonexistent.topo"
Error: File not found: nonexistent.topo
Exit code: 2
```

---

#### must_have: `ensp-cli --version` shows version

**Status:** PASS ✓

**Evidence:**
- File: `src/ensp_cli/cli/main.py`
- Lines 32-36: `version_callback()` function
- Lines 40-48: `--version` option with callback
- File: `src/ensp_cli/__init__.py` - `__version__ = "0.1.0"`

**Runtime verified:**
```
$ ensp-cli --version
ensp-cli version 0.1.0
```

---

#### must_have: CLI is installable via pip and available as `ensp-cli` command

**Status:** PASS ✓

**Evidence:**
- File: `pyproject.toml`
- Line 37: `ensp-cli = "ensp_cli.cli.main:app"` entry point configured
- Installation successful during test run
- CLI command `ensp-cli` available and functional

---

## Test Summary

| Test File | Tests | Status |
|-----------|-------|--------|
| tests/test_models.py | 29 | ✓ All passed |
| tests/test_parser.py | 21 | ✓ All passed |
| **Total** | **50** | **✓ All passed** |

---

## Gaps Summary

### Critical Gaps (Must Fix)
None

### Non-Critical Gaps
None

---

## Recommendations

Phase is complete. Continue to Phase 2.

All success criteria from the roadmap are satisfied:
1. ✓ User can run `ensp-cli list <topo-file>` and see a table of all devices
2. ✓ User can view device connections with `--show-connections`
3. ✓ User receives clear error message for invalid/non-existent `.topo` files
4. ✓ User can export topology data as JSON using `--output json` flag
