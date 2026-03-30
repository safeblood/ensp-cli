# Phase 02: Telnet Connection Layer - Research

**Researched:** 2026-03-30
**Domain:** Python Asyncio Telnet Client, Interactive Console Session Management
**Confidence:** HIGH

## Summary

The Telnet Connection Layer phase requires building an interactive console session management system using Python's `telnetlib3` library. The primary goal is to enable users to connect to eNSP device consoles (exposed as Telnet endpoints at 127.0.0.1:com_port) and start interactive sessions. This is a foundational networking automation pattern well-supported by Python's asyncio ecosystem.

The standard approach uses `telnetlib3` (not the deprecated `telnetlib`) which provides modern asyncio-based Telnet client and server functionality. Key capabilities include automatic IAC (Interpret As Command) sequence handling, proper encoding negotiation, and clean reader/writer stream interfaces. For interactive sessions, the architecture should implement a stdin/stdout passthrough pattern where keyboard input is forwarded to the Telnet connection and received data is printed to the console in real-time.

**Primary recommendation:** Use `telnetlib3` with asyncio for all Telnet operations, implement connection management via async context managers, and use a simple bidirectional pipe pattern for interactive sessions. Huawei VRP prompts follow predictable patterns that can be detected with regex.

## Standard Stack

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| telnetlib3 | 2.x+ | Async Telnet client/server | Official replacement for deprecated telnetlib; RFC-compliant IAC handling; asyncio-native |
| asyncio | 3.11+ | Async I/O event loop | Core Python library; required for telnetlib3; handles concurrent I/O efficiently |
| contextlib | stdlib | Context manager utilities | For creating clean connection management abstractions |

## Architecture Patterns

### Recommended Project Structure

```
src/
├── connection/
│   ├── __init__.py
│   ├── manager.py      # ConnectionManager class
│   ├── session.py      # InteractiveSession class
│   └── telnet_client.py # TelnetClient wrapper
└── console/
    ├── __init__.py
    └── passthrough.py   # Stdin/stdout passthrough utilities
```

### Pattern 1: Connection Manager
**What:** A context manager that handles Telnet connection lifecycle (connect, authenticate, disconnect)
**When to use:** For all Telnet connections to ensure proper cleanup

```python
async with ConnectionManager(host, port) as conn:
    await conn.send_command("display version")
```

### Pattern 2: Interactive Session Passthrough
**What:** Bidirectional data pipe between stdin/stdout and Telnet streams
**When to use:** For `console connect` command where user types directly to device

Two concurrent tasks:
1. **Input Task:** Read from `sys.stdin` → Write to Telnet writer
2. **Output Task:** Read from Telnet reader → Write to `sys.stdout`

### Pattern 3: Prompt Detection
**What:** Regex-based pattern matching for VRP prompt detection
**When to use:** For scripted automation or command execution with confirmation

Common Huawei VRP patterns:
- User mode: `<[^>]+>` (e.g., `<HUAWEI>`)
- System view: `\[[^\]]+\]` (e.g., `[HUAWEI-GigabitEthernet0/0/1]`)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| IAC sequence parsing | Custom byte parser | telnetlib3 | RFC 854/855 compliant; handles WILL/WONT/DO/DONT/SB/SE sequences; escapes 0xFF properly |
| Telnet option negotiation | Manual option state machine | telnetlib3 | Supports BINARY, ECHO, SGA, TERMINAL_TYPE, NAWS automatically |
| Async connection handling | Threading + blocking sockets | asyncio + telnetlib3 | More efficient; single-threaded concurrent I/O; cleaner cancellation |
| Interactive terminal mode | Raw Windows API calls | Python's `sys.stdin.buffer` + `msvcrt` | Cross-platform; sufficient for passthrough |
| Connection cleanup | Manual try/finally blocks | `@asynccontextmanager` | Guarantees cleanup on exceptions; cleaner code |

## Common Pitfalls

### Pitfall 1: IAC Sequence Corruption
**What goes wrong:** Raw 0xFF bytes in data stream are interpreted as commands, causing protocol errors
**How to avoid:** Use telnetlib3 which automatically escapes IAC bytes (0xFF → 0xFF 0xFF) per RFC 854

### Pitfall 2: Encoding Mismatches
**What goes wrong:** Device sends CP437/ASCII but Python decodes as UTF-8, causing decode errors
**How to avoid:** telnetlib3 defaults to locale encoding; for eNSP/Huawei devices, use `encoding='ascii'` with `errors='ignore'` or `errors='replace'`

### Pitfall 3: Prompt Detection Timing
**What goes wrong:** Reading until prompt returns too early (partial output) or hangs indefinitely
**How to avoid:** Use `read_until()` with reasonable timeout; for VRP, wait for `>` or `]` at end of line; implement read buffer accumulation

### Pitfall 4: Windows Console Input Blocking
**What goes wrong:** `input()` blocks and doesn't allow concurrent output display
**How to avoid:** Use `sys.stdin.buffer.read(1)` for character-at-a-time input in a separate asyncio task; use `asyncio.gather()` to run input and output concurrently

### Pitfall 5: CRLF Line Endings
**What goes wrong:** Sending only `\n` when device expects `\r\n`, causing command rejection
**How to avoid:** VRP accepts both; use `\r\n` for strict compliance or let telnetlib3 handle translation

### Pitfall 6: Connection Resource Leaks
**What goes wrong:** Telnet connections left open when program exits or on exception
**How to avoid:** Always use `async with` pattern; ensure `writer.close()` and `await writer.wait_closed()` called in cleanup

## Code Examples

### Basic Telnet Connection

```python
import asyncio
import telnetlib3

async def connect_device(host: str, port: int):
    """Connect to a device via Telnet."""
    try:
        reader, writer = await telnetlib3.open_connection(
            host, 
            port,
            encoding='ascii',
            errors='replace'
        )
        return reader, writer
    except (OSError, asyncio.TimeoutError) as e:
        raise ConnectionError(f"Failed to connect to {host}:{port}: {e}")

# Usage
reader, writer = await connect_device("127.0.0.1", 2000)
```

### Connection Manager (Context Manager Pattern)

```python
from contextlib import asynccontextmanager
import telnetlib3

@asynccontextmanager
async def managed_telnet_connection(host: str, port: int, timeout: int = 10):
    """Async context manager for Telnet connections."""
    reader = None
    writer = None
    try:
        reader, writer = await asyncio.wait_for(
            telnetlib3.open_connection(
                host, 
                port,
                encoding='ascii',
                errors='replace'
            ),
            timeout=timeout
        )
        yield (reader, writer)
    finally:
        if writer:
            writer.close()
            if hasattr(writer, 'wait_closed'):
                await writer.wait_closed()

# Usage
async with managed_telnet_connection("127.0.0.1", 2000) as (reader, writer):
    writer.write("display version\r\n")
    await writer.drain()
    output = await reader.read(4096)
```

### Interactive Session (Stdin/Stdout Passthrough)

```python
import asyncio
import sys

async def telnet_input_task(writer):
    """Forward stdin to Telnet connection."""
    try:
        while True:
            # Read one character at a time for real-time feel
            char = sys.stdin.buffer.read(1)
            if not char:
                break
            writer.write(char.decode('utf-8', errors='replace'))
            await writer.drain()
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        writer.close()

async def telnet_output_task(reader):
    """Forward Telnet output to stdout."""
    try:
        while True:
            data = await reader.read(1024)
            if not data:
                break
            sys.stdout.write(data)
            sys.stdout.flush()
    except asyncio.CancelledError:
        pass

async def interactive_session(host: str, port: int):
    """Start an interactive console session."""
    reader, writer = await telnetlib3.open_connection(
        host, port, 
        encoding='ascii',
        errors='replace'
    )
    
    # Run input and output concurrently
    await asyncio.gather(
        telnet_output_task(reader),
        telnet_input_task(writer),
        return_exceptions=True
    )
```

### VRP Prompt Detection

```python
import re

# Huawei VRP prompt patterns
VRP_PATTERNS = {
    'user_mode': re.compile(r'<[^>]+>\s*$'),           # <HUAWEI>
    'system_view': re.compile(r'\[[^\]]+\]\s*$'),      # [HUAWEI-GigabitEthernet0/0/1]
    'login_prompt': re.compile(r'(?:User|Login|Username).*?:\s*$', re.I),
    'password_prompt': re.compile(r'Password.*?:\s*$', re.I),
}

async def wait_for_prompt(reader, timeout: float = 30.0):
    """Wait for a VRP prompt from the device."""
    buffer = ""
    
    while True:
        try:
            chunk = await asyncio.wait_for(reader.read(1), timeout=timeout)
            if not chunk:
                raise ConnectionError("Connection closed while waiting for prompt")
            
            buffer += chunk
            
            # Check for any prompt pattern
            for name, pattern in VRP_PATTERNS.items():
                if pattern.search(buffer):
                    return name, buffer
                    
        except asyncio.TimeoutError:
            raise TimeoutError(f"Prompt not received within {timeout}s")

# Usage
prompt_type, output = await wait_for_prompt(reader)
print(f"Detected {prompt_type} prompt: {output}")
```

### Command Execution with Prompt Detection

```python
async def send_command(reader, writer, command: str, timeout: float = 10.0) -> str:
    """Send a command and return output until next prompt."""
    # Send command
    writer.write(f"{command}\r\n")
    await writer.drain()
    
    # Read output until prompt
    output = ""
    while True:
        try:
            chunk = await asyncio.wait_for(reader.read(1024), timeout=timeout)
            if not chunk:
                break
            output += chunk
            
            # Check if we have a prompt (command complete)
            if VRP_PATTERNS['user_mode'].search(chunk) or \
               VRP_PATTERNS['system_view'].search(chunk):
                break
        except asyncio.TimeoutError:
            break
    
    return output
```

## Sources

### Primary (HIGH confidence)
- telnetlib3 Official Documentation: https://telnetlib3.readthedocs.io/
- telnetlib3 GitHub Repository: https://github.com/jquast/telnetlib3
- RFC 854 - Telnet Protocol Specification: https://tools.ietf.org/html/rfc854
- RFC 855 - Telnet Option Specifications: https://tools.ietf.org/html/rfc855
- Python asyncio Documentation: https://docs.python.org/3/library/asyncio.html

### Secondary (MEDIUM confidence)
- Huawei VRP CLI Development Guide (Developer documentation for prompt patterns)
- Python contextlib documentation: https://docs.python.org/3/library/contextlib.html
- Netmiko Huawei driver patterns (for VRP prompt regex reference)

### Notes
- telnetlib3 supports Python 3.9+ (project uses 3.11+)
- eNSP device consoles use raw TCP sockets with minimal Telnet negotiation
- Huawei VRP uses ASCII encoding for CLI; UTF-8 not typically needed
- Windows console handling uses `sys.stdin.buffer` for binary input (required for real-time character input)
