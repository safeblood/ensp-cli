# eNSP CLI v1.0.0 Release Notes

**Release Date:** 2026-03-30  
**Version:** 1.0.0  
**Status:** ✅ Released

---

## Summary

eNSP CLI v1.0.0 is the first stable release of the CLI tool for managing Huawei eNSP (Enterprise Network Simulation Platform) topology files and device connections.

---

## Features

### Core Functionality

- ✅ **Topology Parsing**: Parse `.topo` XML files with secure `defusedxml`
- ✅ **Device Management**: List all devices with name, type, model, console port
- ✅ **Connection Viewing**: Show device-to-device connections with interface details
- ✅ **Auto-Discovery**: Automatically find `.topo` files in current directory

### Telnet Operations

- ✅ **Interactive Console**: Connect to devices via Telnet for interactive sessions
- ✅ **Command Execution**: Execute single commands and capture output
- ✅ **VRP Prompt Detection**: Automatic detection of Huawei VRP prompts
- ✅ **Graceful Exit**: Clean session termination with Ctrl+] or Ctrl+D

### Output Formats

- ✅ **Table View**: Rich formatted tables for devices and connections
- ✅ **JSON Output**: Machine-readable JSON for scripting and automation
- ✅ **Visual Topology**: ASCII art topology diagram based on device coordinates
- ✅ **Syntax Highlighting**: Rich syntax highlighting for command output

### CLI Polish

- ✅ **Exit Codes**: Consistent exit codes (0, 1, 2, 3, 4, 5)
- ✅ **Help Documentation**: Comprehensive help for all commands
- ✅ **Version Flag**: `--version` displays version information
- ✅ **Error Messages**: Clear, actionable error messages

---

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `ensp-cli list` | List devices | `ensp-cli list` |
| `ensp-cli list -c` | Show connections | `ensp-cli list -c` |
| `ensp-cli list -o json` | JSON output | `ensp-cli list -o json` |
| `ensp-cli list -o visual` | Visual diagram | `ensp-cli list -o visual` |
| `ensp-cli console` | Interactive session | `ensp-cli console Router1` |
| `ensp-cli exec` | Execute command | `ensp-cli exec Router1 "display version"` |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (device not found, connection failed) |
| 2 | File not found |
| 3 | Invalid XML / Parse error |
| 4 | Permission denied |
| 5 | Command timeout |

---

## Technical Details

### Stack
- **Python**: 3.10+
- **CLI Framework**: Typer 0.15+
- **Models**: Pydantic 2.12+
- **Terminal UI**: Rich 14+
- **Telnet**: telnetlib3 2.0+
- **XML**: defusedxml 0.7+

### Test Coverage
- **Total Tests**: 173
- **Passing**: 173
- **Skipped**: 3
- **Failed**: 0
- **Coverage**: All core functionality tested

### Project Structure
```
ensp-cli/
├── src/ensp_cli/
│   ├── cli/main.py          # Main CLI
│   ├── commands/            # exec.py, console.py
│   ├── models/              # Device, Topology, Connection
│   ├── parser/              # topology_parser.py
│   ├── telnet_client.py     # Async Telnet client
│   └── output.py            # Output formatting
├── tests/                   # 173 tests
└── docs/                    # Documentation
```

---

## Installation

```bash
pip install ensp-cli
```

Or from source:

```bash
git clone https://github.com/yourusername/ensp-cli.git
cd ensp-cli
pip install -e .
```

---

## Requirements

- Python 3.10 or higher
- eNSP installed and running (Windows)
- Telnet enabled on eNSP devices

---

## Known Limitations

- Windows only (eNSP is Windows-only)
- Telnet only (no SSH support in v1.0)
- Single topology file at a time
- No configuration backup/restore yet

---

## Future Roadmap

- **v1.1**: Multi-device operations, batch commands
- **v1.2**: Configuration management, snapshots
- **v2.0**: LLM integration, TextFSM parsing

---

## Acknowledgments

- Built with [Typer](https://typer.tiangolo.com/)
- Terminal UI powered by [Rich](https://rich.readthedocs.io/)
- Async Telnet via [telnetlib3](https://telnetlib3.readthedocs.io/)

---

*Released with ❤️ by the eNSP CLI Team*
