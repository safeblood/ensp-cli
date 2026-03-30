# ensp-cli

## What This Is

A command-line interface for automating Huawei eNSP (Enterprise Network Simulation Platform) lab environments. The CLI parses `.topo` files, manages the eNSP lifecycle (start/stop/load), connects to device consoles via Telnet, executes commands, and saves state as JSON for LLM agent consumption.

## Core Value

Enable rapid, automated network lab setup and teardown with full agent operability via CLI commands and structured JSON state.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Parse eNSP `.topo` XML files to extract device list, types, models, and console ports
- [ ] Start/stop eNSP and load topology files programmatically
- [ ] Connect to device consoles via Telnet (127.0.0.1:com_port)
- [ ] Send CLI commands to individual devices and retrieve output
- [ ] Execute broadcast commands across all devices in a topology
- [ ] Generate new `.topo` files from YAML/JSON topology definitions
- [ ] Export device configurations (read from flash.efz vrpcfg.cfg)
- [ ] Save topology state and command outputs as JSON for agent consumption
- [ ] Rich terminal UI with tables, progress bars, and syntax-highlighted output

### Out of Scope

- GUI or web interface — CLI-only by design, agents operate via commands
- Direct device configuration via SNMP/SSH/NETCONF — console/Telnet only
- Multi-user collaboration features — single-user local tool
- Automatic topology optimization or AI-generated designs — out of scope for v1

## Context

### eNSP File Structure

- `.topo` files are XML containing device definitions with `com_port` attributes (e.g., 2000, 2001)
- Device configs stored in `flash.efz` (zip) as `vrpcfg.cfg` inside device UUID folders
- Console access via `telnet 127.0.0.1 <com_port>` when eNSP is running

### Target Workflow

1. User defines topology in YAML or opens existing `.topo`
2. CLI starts eNSP, loads topology, boots devices
3. CLI connects to consoles, executes commands, captures output
4. State exported as JSON for LLM agents to consume and act upon
5. Cleanup: stop eNSP, archive logs and state

### LLM Integration Strategy

CLI is the interface. Agents call CLI commands (`ensp-cli list`, `ensp-cli exec`, `ensp-cli state`) and parse JSON outputs. No built-in LLM API calls — maximizes flexibility for any agent framework.

## Constraints

- **Tech Stack**: Python 3.10+, Typer for CLI, Rich for UI, telnetlib or telnetlib3 for console access, lxml for XML parsing
- **Platform**: Windows primary (eNSP is Windows-only), may support WSL2 for development
- **eNSP Dependency**: Requires eNSP installed and functional; CLI wraps/interacts with it, doesn't replace it
- **Console Protocol**: Telnet to localhost ports only; no SSH or other protocols in v1

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + Typer + Rich | Modern Python CLI stack with great DX and agent-friendly structured output | — Pending |
| CLI-first for agents | Agents can call commands and parse JSON; no lock-in to specific LLM framework | — Pending |
| Telnet console only | eNSP exposes device consoles as localhost Telnet ports; simplest and most reliable | — Pending |
| YAML for topology definitions | Human-readable, comments support, industry standard for infrastructure-as-code | — Pending |

---
*Last updated: 2026-03-30 after initialization*
