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
# View topology information
ensp-cli topology show <file.topo>

# Connect to devices
ensp-cli device connect <device-name>
```
