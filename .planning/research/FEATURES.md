# Feature Research

**Domain:** Network Lab Automation CLI Tools (Huawei eNSP Focus)
**Researched:** 2026-03-30
**Confidence:** HIGH

## Executive Summary

Network lab automation CLI tools bridge the gap between GUI-based simulators and programmatic network management. Research across GNS3, EVE-NG, Cisco CML, and network automation libraries (Netmiko, Nornir, Scrapli) reveals a clear pattern: **CLI tools succeed when they expose structured data for programmatic consumption** while maintaining human usability. For eNSP specifically, the opportunity lies in parsing the undocumented `.topo` XML format and providing Telnet console automation that existing tools don't support.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Topology listing** | Users need to see what devices exist in a lab | LOW | Parse `.topo` XML to extract device names, types, and IDs |
| **Device console connection** | Core functionality - connecting to device CLI | LOW | Telnet to localhost ports (eNSP uses 2000+port range) |
| **Command execution** | Send commands and see output | LOW | Basic send/expect pattern via Telnet |
| **Start/stop topology** | Control lab lifecycle from CLI | MEDIUM | Automate eNSP GUI interactions or process management |
| **JSON output flag** | Machine-readable output for scripting | LOW | `--output json` on all list/info commands |
| **Help documentation** | Usage instructions and examples | LOW | Standard CLI help with examples |
| **Exit codes** | Success/failure signaling for scripts | LOW | 0=success, non-zero=error (essential for CI/CD) |
| **Configuration file** | Persistent settings (default paths, preferences) | LOW | YAML/JSON config in user's home directory |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Structured command output** | Parse device CLI into JSON (via TextFSM/TTP templates) | MEDIUM | Enables LLM agents to reason about device state without regex |
| **Broadcast commands** | Run same command across all devices in parallel | MEDIUM | Mass configuration/deployment use case |
| **Topology as code** | Generate `.topo` from YAML/JSON definitions | MEDIUM | Git-friendly, reviewable network definitions |
| **LLM agent export** | Export full lab state (devices, configs, topology) as JSON | MEDIUM | Purpose-built for AI agent consumption |
| **Async operations** | Non-blocking device interactions | MEDIUM | Better performance for multi-device operations |
| **Connection pooling** | Reuse Telnet connections for multiple commands | MEDIUM | Performance optimization for batch operations |
| **Config diff/snapshot** | Compare device configs over time | MEDIUM | Track configuration changes |
| **Batch command files** | Execute command scripts against devices | LOW | Text file with one command per line |
| **Interactive shell mode** | REPL-style multi-command session | LOW | Persistent connection for exploration |
| **Topology visualization export** | Generate diagrams from `.topo` (DOT/Mermaid) | MEDIUM | Documentation generation |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **GUI wrapper** | Users want visual feedback | Defeats purpose of CLI; eNSP already has GUI | Focus on structured output that GUIs can consume |
| **SSH support** | "SSH is more secure" | eNSP devices use Telnet-only for console access | Document that Telnet is eNSP's native protocol |
| **Real-time monitoring** | "Show me live stats" | Requires persistent connections, complex state management | Export metrics in Prometheus format periodically |
| **Configuration validation** | Prevent bad configs | Requires deep VRP (Huawei OS) knowledge, fragile | Pass through to device and capture error output |
| **Multi-user coordination** | Team lab sharing | Complex locking, state synchronization conflicts | Document topology state export/import workflow |
| **Plugin architecture** | "Let users extend it" | Adds complexity, maintenance burden | Focus on composable Unix-style pipes with JSON |
| **Built-in templates** | Pre-built configs for common scenarios | Vendor-specific, becomes outdated quickly | Provide examples in documentation instead |

---

## Feature Dependencies

```
[Topology Parsing]
    └──requires──> [.topo File Access]
        └──requires──> [File System Permissions]

[Device Console Automation]
    └──requires──> [Telnet Connection]
        └──requires──> [Device Status Check]
            └──requires──> [Topology Parsing]

[Structured Output]
    └──requires──> [TextFSM/TTP Templates]
        └──requires──> [Device Command Execution]

[Broadcast Commands]
    └──requires──> [Device Console Automation]
        └──requires──> [Async/Parallel Execution]

[Topology Generation]
    └──requires──> [Topology Parsing]
        └──requires──> [XML Generation]

[LLM Agent Export]
    └──requires──> [Structured Output]
        └──requires──> [Device Command Execution]
    └──requires──> [Topology Parsing]
```

### Dependency Notes

- **Device Console requires Topology Parsing:** Must know device names and console ports before connecting
- **Structured Output requires Command Execution:** Need raw CLI output before parsing into structured form
- **Broadcast Commands requires Async Execution:** Need parallel connections to avoid sequential delays
- **LLM Export is composite feature:** Combines topology metadata + structured device state

---

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

- [ ] **Topology listing (`list`)** — Parse `.topo` and show devices with names, types, and console ports
- [ ] **Device console (`console`)** — Interactive Telnet session to single device
- [ ] **Command execution (`exec`)** — Send single command, return output (text mode)
- [ ] **JSON output flag (`--output json`)** — All commands support structured output
- [ ] **Help/version flags** — Standard CLI conventions

**Rationale:** These cover the core loop: see devices → connect → execute → get structured output. Validates that eNSP integration works and users find value in CLI over GUI.

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] **Broadcast commands (`broadcast`)** — Run command on all devices; triggers: users managing multi-device labs
- [ ] **Structured command output (`--parse`)** — Use TextFSM for `show` commands; triggers: users doing config audits
- [ ] **Topology generation (`generate`)** — YAML → `.topo`; triggers: users wanting version-controlled labs
- [ ] **Batch command files (`--file`)** — Execute script of commands; triggers: complex configuration workflows
- [ ] **Config capture (`snapshot`)** — Save all device configs; triggers: backup/restore use cases

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **LLM agent export (`export --format llm`)** — Full lab state for AI consumption; defer: need validation of LLM use cases first
- [ ] **Connection pooling** — Performance optimization; defer: measure actual performance bottlenecks
- [ ] **Topology visualization** — Generate diagrams; defer: evaluate if users actually need this
- [ ] **Plugin system** — Extensibility; defer: wait for clear extension patterns to emerge

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Topology listing | HIGH | LOW | P1 |
| Device console (interactive) | HIGH | LOW | P1 |
| Command execution | HIGH | LOW | P1 |
| JSON output flag | HIGH | LOW | P1 |
| Broadcast commands | HIGH | MEDIUM | P2 |
| Structured command output | HIGH | MEDIUM | P2 |
| Topology generation | MEDIUM | MEDIUM | P2 |
| LLM agent export | MEDIUM | MEDIUM | P3 |
| Config snapshots | MEDIUM | MEDIUM | P2 |
| Connection pooling | LOW | MEDIUM | P3 |
| Topology visualization | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | GNS3 | EVE-NG | Cisco CML | Our Approach |
|---------|------|--------|-----------|--------------|
| CLI tool | Limited (gns3server API) | Limited (REST API) | CML-Free CLI | **First-class CLI for eNSP** |
| Topology format | JSON project files | SQLite + JSON | YAML-based | **Parse existing .topo XML** |
| Console access | Telnet/SSH/VNC | Telnet/SSH/VNC | Console/VNC | **Telnet automation** |
| Structured output | Via API | Via API | JSON API responses | **Native --output json** |
| Batch operations | Via Python SDK | Limited | Via REST API | **Built-in broadcast** |
| Multi-vendor | Yes | Yes | Cisco only | **Huawei VRP focus** |
| LLM integration | None | None | None | **Purpose-built export** |

---

## Key Insights from Research

### Table Stakes Patterns

1. **Every command needs `--output json`**: Modern CLI tools (AWS CLI, `kubectl`, etc.) treat JSON output as non-negotiable. This enables piping to `jq`, scripting, and LLM consumption.

2. **Exit codes matter**: CI/CD pipelines and scripts depend on 0=success, non-zero=failure. Many network tools get this wrong.

3. **Configuration hierarchy**: Follow XDG spec — env vars > config file > defaults. Users expect this.

### Differentiation Opportunities

1. **TextFSM/TTP integration**: Most CLI tools return raw text. Adding structured parsing (like Netmiko's `use_textfsm=True`) is a differentiator for eNSP context.

2. **LLM-native design**: Export formats optimized for LLM context windows (concise JSON, relevant metadata) is underserved in network tooling.

3. **Topology as code**: eNSP's binary `.topo` format is a pain point. YAML-to-topo generation addresses this directly.

### Anti-Pattern Warnings

1. **Interactive by default**: AWS CLI v2's pager change broke CI/CD. Never default to interactive mode.

2. **Breaking output formats**: Once JSON structure is published, it's an API contract. Version and deprecate carefully.

3. **Feature creep**: GNS3's sprawling feature set makes it complex. Focus on CLI-centric workflows.

---

## Sources

- **GNS3 Documentation**: https://docs.gns3.com/ (API reference and project format)
- **EVE-NG Documentation**: https://www.eve-ng.net/ (console access methods, professional features)
- **Cisco CML**: https://developer.cisco.com/docs/modeling-labs/ (YAML topology format)
- **Netmiko**: https://github.com/ktbyers/netmiko (device connection patterns, TextFSM integration)
- **Nornir**: https://nornir.readthedocs.io/ (orchestration patterns, inventory concepts)
- **Scrapli**: https://scrapli.github.io/scrapli/ (high-performance CLI automation patterns)
- **eNSP Usage Guides**: GitHub repositories with `.topo` file analysis
- **TextFSM/TTP**: Network CLI parsing best practices
- **AI Agent CLI Patterns**: https://www.infoq.com/articles/ai-agent-cli/ (structured output design)
- **LLM Structured Output**: https://agenta.ai/blog/the-guide-to-structured-outputs-and-function-calling-with-llms

---
*Feature research for: ensp-cli — A CLI tool for Huawei eNSP automation*
*Researched: 2026-03-30*
