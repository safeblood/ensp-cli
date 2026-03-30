# eNSP CLI

A CLI tool for managing eNSP (Enterprise Network Simulation Platform) topology files and device connections.

## Features

- Parse eNSP topology files (.topo)
- Manage device connections via Telnet
- Execute commands on network devices
- Rich CLI interface with progress indicators

## Installation

```bash
pip install -e .
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Usage

```bash
# List devices in a topology file
ensp-cli list topology.topo

# Connect to a device interactively
ensp-cli console Router1

# Execute a single command on a device
ensp-cli exec Router1 "display version"
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (device not found, connection failed) |
| 2 | File not found |
| 3 | Invalid XML / Parse error |
| 4 | Permission denied |
| 5 | Command timeout |
