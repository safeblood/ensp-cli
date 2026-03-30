# Architecture Research

**Domain:** Python CLI Tools for Network Device Automation (Telnet/SSH)
**Researched:** 2026-03-30
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLI Layer (Typer)                             │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   topo cmd  │  │ device cmd  │  │ config cmd  │  │  exec cmd   │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │
│         │                │                │                │        │
├─────────┴────────────────┴────────────────┴────────────────┴────────┤
│                        Core Services Layer                           │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │  TopologyParser │  │ ProcessManager  │  │   StateManager      │  │
│  │   (.topo XML)   │  │  (eNSP control) │  │   (JSON state)      │  │
│  └────────┬────────┘  └────────┬────────┘  └──────────┬──────────┘  │
│           │                    │                       │            │
│  ┌────────┴────────────────────┴───────────────────────┴────────┐   │
│  │                    ConnectionManager                          │   │
│  │         (Telnet pool, session lifecycle, broadcast)           │   │
│  └────────────────────────────┬──────────────────────────────────┘   │
├───────────────────────────────┼──────────────────────────────────────┤
│                               ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   Transport Layer                            │    │
│  │     ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │    │
│  │     │   Telnet    │    │    SSH      │    │  Console    │  │    │
│  │     │  (pexpect)  │    │  (future)   │    │  (serial)   │  │    │
│  │     └─────────────┘    └─────────────┘    └─────────────┘  │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **CLI Layer** | Parse arguments, route commands, render output | Typer with Rich for formatting |
| **TopologyParser** | Parse .topo XML, extract device definitions, port mappings | xml.etree.ElementTree or lxml |
| **ProcessManager** | Start/stop eNSP processes, load topology files, monitor health | subprocess + psutil for Windows |
| **StateManager** | Maintain topology state, device statuses, export JSON for agents | Pydantic models + JSON files |
| **ConnectionManager** | Manage Telnet sessions, connection pooling, broadcast operations | Custom class with pexpect spawn |
| **CommandExecutor** | Send commands, capture output, handle timeouts/retries | pexpect expect/sendline pattern |
| **ConfigExporter** | Read flash.efz files, extract device configurations | Archive extraction + parsing |
| **TopologyGenerator** | Convert YAML to .topo XML format | Jinja2 templating or XML builder |

## Recommended Project Structure

```
ensp-cli/
├── pyproject.toml              # Project config, dependencies
├── README.md
├── src/
│   └── ensp_cli/
│       ├── __init__.py
│       ├── cli.py              # Typer app entry point
│       ├── commands/           # CLI command implementations
│       │   ├── __init__.py
│       │   ├── topo.py         # Topology management
│       │   ├── device.py       # Device operations
│       │   ├── exec.py         # Command execution
│       │   └── config.py       # Configuration export
│       ├── core/               # Core business logic
│       │   ├── __init__.py
│       │   ├── topology.py     # Topology data models
│       │   ├── device.py       # Device representation
│       │   └── state.py        # State management
│       ├── services/           # Service layer
│       │   ├── __init__.py
│       │   ├── parser.py       # .topo XML parser
│       │   ├── process.py      # eNSP process manager
│       │   ├── connector.py    # Telnet connection handler
│       │   └── executor.py     # Command execution service
│       ├── transport/          # Low-level transport
│       │   ├── __init__.py
│       │   ├── telnet.py       # pexpect Telnet wrapper
│       │   └── base.py         # Abstract transport interface
│       ├── models/             # Pydantic data models
│       │   ├── __init__.py
│       │   ├── topology.py     # Topology models
│       │   ├── device.py       # Device models
│       │   └── state.py        # State export models
│       └── utils/              # Utilities
│           ├── __init__.py
│           ├── xml_helpers.py  # XML parsing utilities
│           └── output.py       # Rich console formatting
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│       └── sample.topo         # Test topology file
└── docs/
```

### Structure Rationale

- **`commands/`**: Separates CLI presentation from business logic. Each command module maps to a CLI subcommand group (typer command groups).
- **`services/`**: Contains the actual business logic that can be tested independently of CLI. Services are injected into commands.
- **`transport/`**: Abstracts network communication. Allows swapping Telnet for SSH or adding new transports without changing service code.
- **`models/`**: Centralized Pydantic models ensure type safety across layers and provide JSON schema for agent consumption.
- **`core/`**: Domain entities and state management that don't depend on external I/O.

## Architectural Patterns

### Pattern 1: Layered Architecture with Clear Boundaries

**What:** Strict separation between CLI (presentation), Services (business logic), and Transport (infrastructure).

**When to use:** Always. This is the foundation for testability and maintainability.

**Trade-offs:**
- ✅ Commands can be tested by mocking services
- ✅ Services can be tested without CLI overhead
- ✅ Transport can be swapped (Telnet ↔ SSH)
- ❌ Slightly more boilerplate than direct implementation

**Example:**
```python
# commands/device.py - CLI layer knows nothing about Telnet
@app.command()
def send_command(
    device: str = typer.Argument(...),
    command: str = typer.Argument(...),
    ctx: typer.Context = typer.Option(None),
):
    """Send command to a single device."""
    executor: CommandExecutor = ctx.obj["executor"]
    result = executor.send(device, command)
    console.print(result.output)

# services/executor.py - Business logic
class CommandExecutor:
    def __init__(self, connector: ConnectionManager):
        self._connector = connector
    
    def send(self, device: str, command: str) -> CommandResult:
        session = self._connector.get_session(device)
        return session.execute(command)

# transport/telnet.py - Infrastructure
class TelnetSession:
    def __init__(self, host: str, port: int):
        self._child = pexpect.spawn(f"telnet {host} {port}")
    
    def execute(self, command: str) -> CommandResult:
        self._child.sendline(command)
        self._child.expect(self._prompt_pattern)
        return CommandResult(output=self._child.before)
```

### Pattern 2: Connection Pool with Session Management

**What:** Maintain persistent connections to devices, reuse sessions, handle reconnection.

**When to use:** When automating multiple operations on the same devices to avoid connection overhead.

**Trade-offs:**
- ✅ Fast subsequent commands (no reconnection)
- ✅ Maintains session state (current config mode)
- ✅ Supports broadcast to multiple devices
- ❌ Must handle connection lifecycle (cleanup on exit)
- ❌ Memory overhead for maintaining sessions

**Example:**
```python
class ConnectionManager:
    def __init__(self):
        self._sessions: dict[str, TelnetSession] = {}
    
    def get_session(self, device_id: str) -> TelnetSession:
        if device_id not in self._sessions:
            self._sessions[device_id] = self._create_session(device_id)
        return self._sessions[device_id]
    
    def broadcast(self, command: str) -> dict[str, CommandResult]:
        results = {}
        for device_id, session in self._sessions.items():
            results[device_id] = session.execute(command)
        return results
    
    def close_all(self):
        for session in self._sessions.values():
            session.close()
```

### Pattern 3: State Export for Agent Consumption

**What:** Export topology and device state as structured JSON that external agents can consume.

**When to use:** When building AI agents or external tools that need to understand the network state.

**Trade-offs:**
- ✅ Enables integration with agent frameworks
- ✅ Machine-readable format
- ✅ Versioned schema for compatibility
- ❌ Must maintain backward compatibility

**Example:**
```python
class StateManager:
    def export_state(self) -> TopologyState:
        return TopologyState(
            topology=self._topology.to_dict(),
            devices=[d.to_dict() for d in self._devices],
            connections=self._get_connections(),
            timestamp=datetime.utcnow().isoformat()
        )
    
    def save_state(self, path: Path):
        state = self.export_state()
        path.write_text(state.model_dump_json(indent=2))
```

## Data Flow

### Command Execution Flow

```
User CLI Input
       ↓
┌──────────────┐
│ Typer parses │
│ arguments    │
└──────┬───────┘
       ↓
┌──────────────┐
│ Command gets │
│ service from │
│ DI context   │
└──────┬───────┘
       ↓
┌─────────────────────┐
│ Service calls       │
│ ConnectionManager   │
└──────┬──────────────┘
       ↓
┌─────────────────────┐
│ ConnectionManager   │
│ routes to Telnet    │
│ session or creates  │
└──────┬──────────────┘
       ↓
┌─────────────────────┐
│ pexpect sends cmd,  │
│ waits for prompt    │
└──────┬──────────────┘
       ↓
┌─────────────────────┐
│ Output flows back   │
│ through layers      │
└──────┬──────────────┘
       ↓
┌─────────────────────┐
│ Rich formats and    │
│ displays result     │
└─────────────────────┘
```

### State Management Flow

```
┌─────────────────────────────────────────────────────┐
│                    StateManager                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │   Topology   │  │    Devices   │  │ Sessions   │ │
│  │    State     │  │    State     │  │   State    │ │
│  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘ │
└─────────┼─────────────────┼────────────────┼────────┘
          │                 │                │
          └─────────────────┴────────────────┘
                            ↓
                   ┌────────────────┐
                   │  Export as     │
                   │  Pydantic JSON │
                   └───────┬────────┘
                           ↓
                   ┌────────────────┐
                   │  Write to file │
                   │  or stdout     │
                   └────────────────┘
```

### Key Data Flows

1. **Topology Loading:** `.topo file` → XML Parser → Topology Model → State Manager
2. **Device Connection:** State Manager → Connection Manager → Telnet Session → Device Console
3. **Command Broadcast:** CLI → Command Executor → Connection Manager → All Sessions → Aggregated Results
4. **State Export:** State Manager → Pydantic Models → JSON File (for agent consumption)

## Suggested Build Order

Based on dependency analysis, build in this order:

| Phase | Component | Dependencies | Rationale |
|-------|-----------|--------------|-----------|
| 1 | Models (Pydantic) | None | Foundation data structures used everywhere |
| 2 | XML Parser | Models | Reads topology into models |
| 3 | State Manager | Models, Parser | Central state coordination |
| 4 | Process Manager | State Manager | Can load/save topology state |
| 5 | Telnet Transport | None | Low-level, test independently |
| 6 | Connection Manager | Transport, Models | Manages multiple transports |
| 7 | Command Executor | Connection Manager | Uses sessions to execute |
| 8 | CLI Commands | All above | Thin layer over services |
| 9 | Config Exporter | Parser, Models | Specialized functionality |
| 10 | Topology Generator | Models | YAML → .topo conversion |

### Dependency Graph

```
                    ┌─────────────┐
                    │    CLI      │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   Commands    │  │    Config     │  │   Topology    │
│   (exec)      │  │   Exporter    │  │  Generator    │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  Command Executor   │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Connection Manager  │
                └──────────┬──────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
    ┌──────────────────┐    ┌──────────────────┐
    │  Telnet Transport │    │ Process Manager │
    │    (pexpect)      │    └────────┬─────────┘
    └──────────────────┘             │
                                     ▼
                          ┌────────────────────┐
                          │    State Manager   │
                          └─────────┬──────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
            ┌──────────────┐ ┌──────────────┐ ┌──────────┐
            │ Topology     │ │   Device     │ │  XML     │
            │   Models     │ │   Models     │ │ Parser   │
            └──────────────┘ └──────────────┘ └──────────┘
```

## Scaling Considerations

Since eNSP runs locally with limited device count (typically <50 devices per topology), scaling concerns are minimal. However:

| Scale | Consideration | Approach |
|-------|---------------|----------|
| <10 devices | Simple sequential execution | Single-threaded, simple connection dict |
| 10-50 devices | Concurrent connections | ThreadPoolExecutor for parallel operations |
| 50+ devices | Connection limits | Connection pooling with LRU eviction |

### Performance Priorities

1. **Connection reuse:** Persistent Telnet sessions are faster than reconnecting each command
2. **Parallel execution:** Use `ThreadPoolExecutor` for broadcast commands across multiple devices
3. **Lazy loading:** Parse .topo file once, cache topology model

## Anti-Patterns

### Anti-Pattern 1: Mixing CLI and Business Logic

**What people do:** Put pexpect code directly in Typer command functions.

**Why it's wrong:** Commands become untestable, can't reuse logic, hard to switch transports.

**Do this instead:** 
```python
# WRONG
@app.command()
def bad_command():
    child = pexpect.spawn("telnet 192.168.1.1")
    child.sendline("show version")
    ...

# RIGHT
@app.command()
def good_command(executor: CommandExecutor = Depends(get_executor)):
    result = executor.execute("device1", "show version")
```

### Anti-Pattern 2: No Session Cleanup

**What people do:** Open Telnet connections without ensuring they close.

**Why it's wrong:** Leaks connections, leaves hanging sessions, port exhaustion.

**Do this instead:** Use context managers and atexit handlers:
```python
class ConnectionManager:
    def __init__(self):
        atexit.register(self.close_all)
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close_all()
```

### Anti-Pattern 3: Blocking Operations in CLI

**What people do:** Execute long-running commands synchronously without feedback.

**Why it's wrong:** Users think the tool is frozen; no progress visibility.

**Do this instead:** Use Rich progress bars and status spinners:
```python
with console.status("[bold green]Connecting to devices...") as status:
    for device in devices:
        status.update(f"[bold green]Connecting to {device}...")
        connector.connect(device)
```

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| eNSP Process | subprocess + psutil | Monitor process state, restart if needed |
| Device Console | Telnet via pexpect | Expect patterns for different device types |
| Agent Framework | JSON state export | Pydantic models ensure schema compatibility |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| CLI ↔ Services | Dependency injection via Typer context | Services passed in `ctx.obj` |
| Services ↔ Transport | Abstract interface | Allows mocking for tests |
| Parser ↔ Models | Pydantic constructors | Parser creates model instances |
| State Manager ↔ All | Event callbacks | Optional pub/sub for state changes |

## Sources

- [Typer Documentation](https://typer.tiangolo.com/) - CLI framework built on Click
- [Pexpect Documentation](https://pexpect.readthedocs.io/) - Expect pattern for Python
- [Netmiko Patterns](https://github.com/ktbyers/netmiko) - Network device connection patterns
- [Rich Console](https://rich.readthedocs.io/) - Terminal formatting and progress
- [Python Network Automation Libraries 2026](https://blog.cloudmylab.com/python-libraries-network) - Current ecosystem overview
- [TextFSM/NTC Templates](https://github.com/networktocode/ntc-templates) - Structured output parsing

---
*Architecture research for: ensp-cli - Python CLI for eNSP Network Automation*
*Researched: 2026-03-30*
