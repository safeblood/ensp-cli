# Project Roadmap

**Project:** ensp-cli  
**Version:** v1.0.0  
**Created:** 2026-03-30

---

## Phase 1: Foundation & Topology Parsing

**Goal:** Establish data models and enable topology file parsing

**Requirements Mapped:**
| Requirement | Description |
|-------------|-------------|
| TOPO-01 | Parse `.topo` XML files and list all devices with names, types, models, and console ports |
| TOPO-02 | View topology structure including device-to-device connections |

**Success Criteria:**
1. User can run `ensp-cli list <topo-file>` and see a table of all devices with their names, types, models, and console ports
2. User can view device connections showing which devices are linked together
3. User receives a clear error message when providing an invalid or non-existent `.topo` file
4. User can export topology data as JSON using `--output json` flag

**Key Components:**
- Pydantic models (Device, Topology, Connection)
- XML parser using `defusedxml` for secure parsing
- `list` command implementation

**Research Notes:**
- Use `defusedxml` to prevent XXE vulnerabilities
- Build order: Models first, then XML parser

---

## Phase 2: Telnet Connection Layer

**Goal:** Enable interactive console sessions with devices

**Requirements Mapped:**
| Requirement | Description |
|-------------|-------------|
| CONN-01 | Connect to device console via Telnet (127.0.0.1:com_port) |
| CONN-02 | Start an interactive console session with a single device |

**Success Criteria:**
1. User can run `ensp-cli console <device-name>` and enter an interactive Telnet session with the device
2. User sees device output in real-time during the interactive session
3. User can exit the console session gracefully and return to the shell
4. User receives a helpful error when the device is unreachable or Telnet connection fails

**Key Components:**
- Telnet transport layer using `telnetlib3`
- Connection manager for session handling
- `console` command implementation

**Research Notes:**
- Handle Telnet IAC escape sequences to prevent output corruption
- Implement robust prompt pattern detection for Huawei VRP

---

## Phase 3: Command Execution & CLI Polish

**Goal:** Enable command execution and complete CLI functionality

**Requirements Mapped:**
| Requirement | Description |
|-------------|-------------|
| EXEC-01 | Execute a single command on a device and return the output |
| CLI-01 | All commands support `--output json` for machine-readable output |
| CLI-02 | CLI provides help documentation and version flags |
| CLI-03 | CLI returns appropriate exit codes (0=success, non-zero=failure) |

**Success Criteria:**
1. User can run `ensp-cli exec <device-name> "<command>"` and see the command output
2. User can use `--output json` on any command to get structured, machine-readable output
3. User can run `ensp-cli --help` to see available commands and `ensp-cli --version` to see version
4. User can check exit code (`$?` or `%ERRORLEVEL%`) to determine if a command succeeded (0) or failed (non-zero)
5. User receives command output with proper formatting and syntax highlighting in terminal

**Key Components:**
- Command executor service
- Output formatter (text and JSON modes)
- Exit code handling
- Rich terminal formatting

**Research Notes:**
- Typer provides built-in help and version flags
- JSON output essential for LLM/agent integration

---

## Summary

| Phase | Name | Requirements | Success Criteria |
|-------|------|--------------|------------------|
| 1 | Foundation & Topology Parsing | TOPO-01, TOPO-02 | 4 |
| 2 | Telnet Connection Layer | CONN-01, CONN-02 | 4 |
| 3 | Command Execution & CLI Polish | EXEC-01, CLI-01, CLI-02, CLI-03 | 5 |

**Total:** 3 phases, 8 v1 requirements, 13 success criteria

---

## Phase Ordering Rationale

1. **Foundation before Connection:** Must parse topology to know device names and console ports before connecting
2. **Connection before Execution:** Need stable Telnet transport before executing commands remotely
3. **Core features before polish:** CLI output formatting depends on having functional commands

This ordering follows the research-recommended build order: Models → XML Parser → Telnet Transport → CLI Commands

---

## Future Phases (Post-v1)

- **Phase 4:** Multi-Device Operations (broadcast commands, batch execution)
- **Phase 5:** Configuration Management (snapshots, exports)
- **Phase 6:** Structured Output & LLM Integration (TextFSM, agent export)

---

*Last updated: 2026-03-30 after roadmap creation*
