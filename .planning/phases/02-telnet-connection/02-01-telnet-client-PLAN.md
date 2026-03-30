---
wave: 1
depends_on: []
files_modified:
  - src/ensp_cli/telnet_client.py
  - src/ensp_cli/connection_manager.py
  - tests/test_telnet_client.py
  - tests/test_connection_manager.py
autonomous: true
---

# Plan: Telnet Client & Connection Manager

## Goal
Create a robust async Telnet client and connection manager that handles device connections using telnetlib3, with proper lifecycle management and VRP prompt detection.

## Tasks

<task id="1" name="Add telnetlib3 dependency">
Add telnetlib3 to project dependencies for async Telnet support.

- Add `telnetlib3>=2.0" to pyproject.toml dependencies
- Ensure minimum Python 3.11 compatibility
- Update lock file if using uv/pdm

<verify>
Run `pip install -e .` or `uv sync` and verify telnetlib3 installs without errors.
</verify>
</task>

<task id="2" name="Create TelnetClient class">
Create `src/ensp_cli/telnet_client.py` with TelnetClient class.

Features:
- Async connection to 127.0.0.1:port
- Read/write methods with timeout support
- Encoding: ascii with errors='replace' for VRP compatibility
- VRP prompt detection patterns:
  - User view: `<Hostname>` (e.g., `<Huawei>`)
  - System view: `[Hostname]` (e.g., `[Huawei-GigabitEthernet0/0/1]`)
- Clean disconnection with writer.close() and wait_closed()

Class interface:
```python
class TelnetClient:
    def __init__(self, host: str, port: int, timeout: float = 10.0)
    async def connect(self) -> None
    async def read_until(self, pattern: str | re.Pattern, timeout: float | None = None) -> str
    async def read_available(self) -> str
    async def write(self, data: str) -> None
    async def write_line(self, data: str) -> None
    async def close(self) -> None
    @property
    def is_connected(self) -> bool
```

<verify>
- TelnetClient can be instantiated with host/port
- connect() establishes TCP connection
- read_until() returns data when pattern matches
- write_line() sends data with newline
- close() cleans up resources
</verify>
</task>

<task id="3" name="Create ConnectionManager">
Create `src/ensp_cli/connection_manager.py` with ConnectionManager class.

Features:
- Context manager for session lifecycle
- Automatic connection cleanup on exit
- Connection pooling (single device per session)
- Error handling for connection failures

Class interface:
```python
@asynccontextmanager
async def device_session(device: Device, timeout: float = 10.0) -> AsyncGenerator[TelnetClient, None]:
    """Context manager for device Telnet session."""
```

Additional functions:
```python
async def get_device_by_name(topology: Topology, name: str) -> Device | None
async def connect_to_device(device: Device, timeout: float = 10.0) -> TelnetClient
```

<verify>
- device_session context manager works with async with
- Connection established when entering context
- Connection closed when exiting context (even on exception)
- Connection errors raise ConnectionError with helpful message
</verify>
</task>

<task id="4" name="Add VRP prompt patterns">
Add regex patterns for VRP prompt detection.

Patterns to detect:
- User mode: `^<[\w\-]+>$` (e.g., `<Huawei>`)
- System mode: `^\[[\w\-]+\]$` (e.g., `[Huawei]`)
- Interface mode: `^\[[\w\-]+-[\w\/\-]+\]$` (e.g., `[Huawei-GigabitEthernet0/0/1]`)

Create constants:
```python
VRP_PROMPT_USER = re.compile(r"^<[\w\-]+>$", re.MULTILINE)
VRP_PROMPT_SYSTEM = re.compile(r"^\[[\w\-]+(?:-[\w\/\-]+)*\]$", re.MULTILINE)
VRP_PROMPT_ANY = re.compile(r"(?:<[\w\-]+>|\[[\w\-]+(?:-[\w\/\-]+)*\])$", re.MULTILINE)
```

<verify>
- Patterns match actual VRP prompts
- Patterns don't match command output accidentally
- Unit tests verify pattern matching
</verify>
</task>

<task id="5" name="Write unit tests">
Create comprehensive tests for telnet client and connection manager.

Test files:
- `tests/test_telnet_client.py`: Test TelnetClient class
- `tests/test_connection_manager.py`: Test ConnectionManager

Use mocking for telnetlib3 to avoid requiring actual devices.

Test coverage:
- Connection establishment
- Read/write operations
- Timeout handling
- Connection errors
- Context manager cleanup
- VRP prompt detection

<verify>
- All tests pass with `pytest tests/test_telnet_client.py tests/test_connection_manager.py -v`
- Coverage > 90% for new code
</verify>
</task>

## must_haves

Goal: Create a robust async Telnet client and connection manager

- [ ] telnetlib3 dependency installed and importable
- [ ] TelnetClient class with connect/read/write/close methods
- [ ] Connection manager with async context manager
- [ ] VRP prompt detection patterns implemented
- [ ] Unit tests with mocking for telnetlib3
- [ ] Clean resource cleanup on connection failure
