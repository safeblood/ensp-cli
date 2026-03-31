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

| Phase | Name | Requirements | Success Criteria | Status |
|-------|------|--------------|------------------|--------|
| 1 | Foundation & Topology Parsing | TOPO-01, TOPO-02 | 4 | ✅ |
| 2 | Telnet Connection Layer | CONN-01, CONN-02 | 4 | ✅ |
| 3 | Command Execution & CLI Polish | EXEC-01, CLI-01, CLI-02, CLI-03 | 5 | ✅ |
| 4 | Device Operations (Read-Only Helpers) | TOPO-03, TOPO-04, TOPO-05, TOPO-06 | 6 | ✅ |
| 5 | Device Lifecycle Management | LIFECYCLE-01~06 | 7 | 🔵 |

**Total:** 5 phases, 18 requirements, 26 success criteria

---

## Phase Ordering Rationale

1. **Foundation before Connection:** Must parse topology to know device names and console ports before connecting
2. **Connection before Execution:** Need stable Telnet transport before executing commands remotely
3. **Core features before polish:** CLI output formatting depends on having functional commands

This ordering follows the research-recommended build order: Models → XML Parser → Telnet Transport → CLI Commands

---

## Phase 4: Device Operations (Read-Only Helpers)

**Goal:** Provide read-only helper commands for device configuration viewing, export, and comparison

**Note:** Phase 4 was redefined from "topology modification" to "read-only helpers" because eNSP does not watch .topo file changes.

**Requirements Mapped:**
| Requirement | Description |
|-------------|-------------|
| TOPO-03 | View device configuration |
| TOPO-04 | Export device configuration |
| TOPO-05 | Compare configurations |
| TOPO-06 | Audit configuration consistency |

**Success Criteria:**
1. User can view config with `ensp-cli show-config <device>`
2. User can export config with `ensp-cli export-config <device> -o <file>`
3. User can compare configs with `ensp-cli diff-config <dev1> <dev2>`
4. User can audit configs with `ensp-cli audit-configs`
5. Import configs with `ensp-cli import-config <device> <file>`
6. Batch command execution with `ensp-cli exec-batch`

**Key Components:**
- Config viewing commands (show-config, show-interfaces, show-routes)
- Config exporter service
- Config importer service
- Config differ service
- Import/export with multiple formats

---

## Phase 5: Device Lifecycle Management

**Goal:** Enable independent device launching and management without eNSP GUI

**Research Findings:**
- New eNSP (>=1.3) uses Huawei's lightweight virtualization engine
- Router process: `eNSP_Router.exe` with `sim` parameter
- Switch process: `eNSP_Switch.exe` with `sim` parameter
- Base images: `.vdi` format in `vboxserver/` directory
- Console ports: Auto-assigned (2000, 2001, ...)
- Each device needs unique MAC address

**Requirements Mapped:**
| Requirement | Description |
|-------------|-------------|
| LIFECYCLE-01 | Launch router devices independently |
| LIFECYCLE-02 | Launch switch devices independently |
| LIFECYCLE-03 | Stop running devices |
| LIFECYCLE-04 | View running device status |
| LIFECYCLE-05 | Launch all devices from topology |
| LIFECYCLE-06 | Auto-assign console ports |

**Success Criteria:**
1. User can launch router: `ensp-cli launch-router R1 --model AR2220`
2. User can launch switch: `ensp-cli launch-switch S1 --model S5700`
3. User can stop device: `ensp-cli stop-device R1`
4. User can view running devices: `ensp-cli ps`
5. User can launch topology: `ensp-cli launch-topology lab.topo`
6. Console ports auto-assigned, no conflicts
7. Devices reachable via Telnet after launch

**Key Components:**
- Device launcher service
- Process manager (track PIDs)
- Port allocator (2000-2100 range)
- MAC address generator
- Device readiness detector
- Running state persistence

---

## Future Phases (Post-v1.2)

- **Phase 6:** Multi-Device Operations (broadcast commands, batch execution)
- **Phase 7:** Configuration Management (snapshots, exports)
- **Phase 8:** Structured Output & LLM Integration (TextFSM, agent export)

---

*Last updated: 2026-03-30 after roadmap creation*
