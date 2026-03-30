---
wave: 1
depends_on: []
files_modified: []
autonomous: true
---

# Plan 02: XML Topology Parser Implementation

## Goal
Implement secure XML parser using defusedxml to parse eNSP .topo files and convert to Topology model.

## Tasks

<task id="1" name="Analyze eNSP .topo file format">
Research and document the eNSP topology XML structure.

Key elements to identify:
- Device nodes (name, type, model, com_port attributes)
- Connection nodes (from_device, from_port, to_device, to_port)
- Topology metadata

<verify>
- Document XML element structure for devices
- Document XML element structure for connections
- Note any namespace handling requirements
</verify>
</task>

<task id="2" name="Create secure XML parser">
Implement parser using defusedxml with XXE protection.

Parser class TopologyParser:
- parse_file(path: Path) -> Topology: Parse .topo file to Topology model
- parse_string(xml_content: str) -> Topology: Parse XML string (for testing)

Security requirements:
- Use defusedxml.ElementTree.parse() instead of xml.etree
- Set entity expansion limits
- Handle XML bomb attacks gracefully

<verify>
- Parser uses defusedxml, not stdlib xml.etree
- Parser handles XML parsing errors gracefully with clear error messages
- XXE attack payload is safely rejected or ignored
</verify>
</task>

<task id="3" name="Implement device extraction">
Parse device elements from XML and create Device models.

Device XML attributes to extract:
- name: Device identifier
- type: Device category (Router, Switch, etc.)
- model: Specific hardware model
- com_port: Console port for Telnet access

Edge cases:
- Missing attributes should raise clear error
- Invalid com_port format should raise validation error
- Unknown device types should be accepted (pass through)

<verify>
- Correctly extracts all devices from sample .topo file
- Creates valid Device instances for each
- Handles missing attributes with clear error messages
</verify>
</task>

<task id="4" name="Implement connection extraction">
Parse connection elements from XML and create Connection models.

Connection XML attributes to extract:
- from_device: Source device name
- from_port: Source interface
- to_device: Target device name  
- to_port: Target interface

Validation:
- Both devices referenced must exist in topology
- Port format should be preserved as-is

<verify>
- Correctly extracts all connections from sample .topo file
- Creates valid Connection instances for each
- Validates that connected devices exist
</verify>
</task>

<task id="5" name="Add error handling and validation">
Implement comprehensive error handling for malformed files.

Error cases:
- File not found → FileNotFoundError with clear message
- Invalid XML → ParseError with line/column info
- Missing required elements → ValueError with details
- Invalid device references in connections → ValueError

<verify>
- Non-existent file raises FileNotFoundError
- Malformed XML raises ParseError
- Missing devices in connection references detected
- Error messages are user-friendly
</verify>
</task>

<task id="6" name="Export parser from package">
Add parser to public API.

Exports:
- TopologyParser

<verify>
- `from ensp_cli.parser import TopologyParser` works
- Parser is accessible from main package
</verify>
</task>

## must_haves

Goal: Implement secure XML parser using defusedxml to parse eNSP .topo files

- [ ] Parser uses defusedxml for XXE protection
- [ ] Parser correctly extracts all devices from .topo files
- [ ] Parser correctly extracts all connections from .topo files
- [ ] Invalid/malformed files produce clear error messages
- [ ] File not found produces clear error message
- [ ] Parser can be imported from ensp_cli.parser
