# Requirements

## v1 Requirements (MVP)

### Topology (TOPO)
- [ ] **TOPO-01**: User can parse `.topo` XML files and list all devices with names, types, models, and console ports
- [ ] **TOPO-02**: User can view topology structure including device-to-device connections

### Connection (CONN)
- [ ] **CONN-01**: User can connect to device console via Telnet (127.0.0.1:com_port)
- [ ] **CONN-02**: User can start an interactive console session with a single device

### Execution (EXEC)
- [ ] **EXEC-01**: User can execute a single command on a device and return the output

### CLI (CLI)
- [ ] **CLI-01**: All commands support `--output json` for machine-readable output
- [ ] **CLI-02**: CLI provides help documentation and version flags
- [ ] **CLI-03**: CLI returns appropriate exit codes (0=success, non-zero=failure)

## v2 Requirements (Post-Validation)

### Connection (CONN)
- [ ] **CONN-03**: User can run broadcast commands across all devices in parallel

### Configuration (CONF)
- [ ] **CONF-01**: User can use a configuration file for default settings (paths, preferences)
- [ ] **CONF-02**: User can save snapshots of all device configurations

### Parsing (PARSE)
- [ ] **PARSE-01**: User can get structured command output using TextFSM/TTP templates

### Generation (GEN)
- [ ] **GEN-01**: User can generate `.topo` files from YAML/JSON definitions

### LLM Integration (LLM)
- [ ] **LLM-01**: User can export full lab state in LLM-optimized format

## Out of Scope

| Feature | Reason |
|---------|--------|
| SSH support | eNSP uses Telnet-only for console access; SSH would be misleading |
| GUI wrapper | Defeats CLI-first purpose; agents consume structured output, not GUI |
| Real-time monitoring | Adds complexity without validated use case; defer until requested |
| Plugin architecture | Premature abstraction; focus on composable Unix-style pipes with JSON |
| Configuration validation | Requires deep VRP knowledge; pass through to device and capture errors instead |
| Multi-user coordination | Complex locking and state sync; single-user tool for v1-v2 |

## Traceability

| Requirement | Phase | Implementation |
|-------------|-------|----------------|
| TOPO-01 | 1 | TopologyParser class, `list` command |
| TOPO-02 | 1 | Connection parsing in TopologyParser |
| CONN-01 | 2 | TelnetTransport class using telnetlib3 |
| CONN-02 | 2 | `console` command with interactive session |
| EXEC-01 | 3 | `exec` command, CommandExecutor service |
| CLI-01 | 3 | Output formatter with JSON mode |
| CLI-02 | 3 | Typer built-in help and version flags |
| CLI-03 | 3 | Exit code handling in CLI commands |

---
*Last updated: 2026-03-30 after requirements definition*
