---
wave: 1
depends_on: []
files_modified: []
autonomous: true
---

# Plan 01: Project Setup and Pydantic Models

## Goal
Establish project structure with modern Python tooling and create Pydantic data models for topology domain entities.

## Tasks

<task id="1" name="Create project structure and pyproject.toml">
Initialize Python project with src layout and all dependencies.

Project structure:
```
ensp-cli/
├── pyproject.toml
├── README.md
├── src/
│   └── ensp_cli/
│       ├── __init__.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── device.py
│       │   ├── connection.py
│       │   └── topology.py
│       ├── parser/
│       │   ├── __init__.py
│       │   └── topology_parser.py
│       └── cli/
│           ├── __init__.py
│           └── main.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── test_models.py
```

Dependencies in pyproject.toml:
- pydantic >=2.10.0
- defusedxml >=0.7.1
- typer >=0.15.0
- rich >=13.0.0
- pytest >=8.0.0 (dev)

<verify>
- pyproject.toml exists with all dependencies
- src/ensp_cli directory structure created
- Can run `pip install -e .` successfully
</verify>
</task>

<task id="2" name="Create Device Pydantic model">
Implement Device model with all required fields.

Fields:
- name: str (device identifier from XML)
- device_type: str (e.g., "Router", "Switch", "Firewall")
- model: str (e.g., "AR2220", "S5700")
- console_port: int (Telnet port number)

Validation:
- console_port must be positive integer (1-65535)
- name must be non-empty string

<verify>
- Device model can be instantiated with valid data
- Validation errors raised for invalid console_port (0, -1, 70000)
- Validation errors raised for empty name
</verify>
</task>

<task id="3" name="Create Connection Pydantic model">
Implement Connection model representing device-to-device links.

Fields:
- from_device: str (source device name)
- from_port: str (source interface, e.g., "GE0/0/0")
- to_device: str (target device name)
- to_port: str (target interface, e.g., "GE0/0/1")

Validation:
- All string fields must be non-empty
- from_device and to_device cannot be the same

<verify>
- Connection model can be instantiated with valid data
- Validation error when from_device == to_device
- Validation error for empty port strings
</verify>
</task>

<task id="4" name="Create Topology aggregate model">
Implement Topology model as aggregate root containing devices and connections.

Fields:
- name: str (topology name from filename or XML)
- devices: List[Device]
- connections: List[Connection]
- file_path: Path | None (source .topo file)

Methods:
- get_device(name: str) -> Device | None: Find device by name
- get_connections_for(device_name: str) -> List[Connection]: Get all connections for a device
- device_count: int property

<verify>
- Topology model can be created with devices and connections
- get_device() returns correct device or None
- get_connections_for() filters correctly
- device_count property works
</verify>
</task>

<task id="5" name="Export models from package">
Create clean public API in models/__init__.py.

Exports:
- Device
- Connection  
- Topology

<verify>
- `from ensp_cli.models import Device, Connection, Topology` works
- All models accessible from single import
</verify>
</task>

## must_haves

Goal: Establish project structure with modern Python tooling and create Pydantic data models

- [ ] Project can be installed with `pip install -e .`
- [ ] Device model validates name, type, model, and console port
- [ ] Connection model validates device-to-device links
- [ ] Topology model aggregates devices and connections
- [ ] All models have proper type hints and validation
- [ ] Models can be imported from ensp_cli.models
