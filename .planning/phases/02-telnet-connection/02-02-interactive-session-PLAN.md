---
wave: 2
depends_on:
  - 02-01-telnet-client-PLAN.md
files_modified:
  - src/ensp_cli/interactive_session.py
  - tests/test_interactive_session.py
autonomous: true
---

# Plan: Interactive Console Session

## Goal
Implement interactive console session that pipes user input to the Telnet connection and displays device output in real-time, with graceful exit handling.

## Tasks

<task id="1" name="Create InteractiveSession class">
Create `src/ensp_cli/interactive_session.py` with InteractiveSession class.

Features:
- Bidirectional data pipe: stdin ↔ Telnet ↔ stdout
- Real-time output display (no buffering)
- Handle special keys (Ctrl+C, Ctrl+D, Ctrl+])
- Graceful exit on disconnect or user request

Class interface:
```python
class InteractiveSession:
    def __init__(self, client: TelnetClient)
    async def start(self) -> None
    async def stop(self) -> None
    async def _input_reader(self) -> None  # stdin → Telnet
    async def _output_reader(self) -> None  # Telnet → stdout
```

Implementation notes:
- Use asyncio.gather() to run input_reader and output_reader concurrently
- Use asyncio.Queue for input buffering
- Handle Windows console with msvcrt for non-blocking input
- Use sys.stdout.write() with flush=True for real-time output

<verify>
- InteractiveSession can be instantiated with TelnetClient
- start() begins bidirectional communication
- stop() cleanly terminates both directions
- Ctrl+C or exit command triggers clean shutdown
</verify>
</task>

<task id="2" name="Implement stdin to Telnet forwarding">
Implement non-blocking stdin reader that forwards input to Telnet.

Implementation:
```python
async def _input_reader(self) -> None:
    """Read from stdin and write to Telnet."""
    while self._running:
        try:
            char = await self._read_char()
            if char == '\x03':  # Ctrl+C
                self._running = False
                break
            elif char == '\x04':  # Ctrl+D
                self._running = False
                break
            elif char == '\x1d':  # Ctrl+]
                self._running = False
                break
            await self._client.write(char)
        except asyncio.CancelledError:
            break
```

Platform handling:
- Windows: Use asyncio.to_thread() with msvcrt.getch()
- Unix: Use asyncio.to_thread() with sys.stdin.read(1)

<verify>
- Keystrokes sent immediately to Telnet
- Special keys (Ctrl+C, Ctrl+D, Ctrl+]) trigger exit
- No input buffering delays
</verify>
</task>

<task id="3" name="Implement Telnet to stdout forwarding">
Implement async reader that displays device output in real-time.

Implementation:
```python
async def _output_reader(self) -> None:
    """Read from Telnet and write to stdout."""
    while self._running:
        try:
            data = await self._client.read_available()
            if data:
                sys.stdout.write(data)
                sys.stdout.flush()
            else:
                await asyncio.sleep(0.01)  # Small delay to prevent busy-wait
        except asyncio.CancelledError:
            break
        except ConnectionError:
            print("\n[Connection lost]", file=sys.stderr)
            self._running = False
            break
```

<verify>
- Device output appears immediately on screen
- Connection loss detected and reported
- No output buffering delays
</verify>
</task>

<task id="4" name="Add session banners and help">
Add user-friendly session start/end messages.

Features:
- Display connection info on start: "Connected to <device-name> at 127.0.0.1:<port>"
- Display exit instructions: "Press Ctrl+] or type 'exit' to exit"
- Display disconnection message on exit
- Handle connection errors with helpful messages

Error messages:
- Connection refused: "Cannot connect to <device>. Is the device running in eNSP?"
- Timeout: "Connection to <device> timed out. Check if device is responsive."
- Network unreachable: "Cannot reach <device>. Check network configuration."

<verify>
- Connection banner shows device name and port
- Exit instructions displayed
- Error messages are actionable and specific
</verify>
</task>

<task id="5" name="Write unit tests">
Create tests for interactive session using mocks.

Test coverage:
- Session start/stop lifecycle
- Input forwarding (stdin → Telnet)
- Output forwarding (Telnet → stdout)
- Exit key handling (Ctrl+C, Ctrl+D, Ctrl+])
- Connection error handling
- Session cleanup on abnormal termination

Use monkeypatch for stdin/stdout mocking.

<verify>
- All tests pass with `pytest tests/test_interactive_session.py -v`
- Coverage > 80% for interactive session code
</verify>
</task>

## must_haves

Goal: Implement interactive console session with real-time bidirectional I/O

- [ ] InteractiveSession class with start/stop methods
- [ ] stdin forwarded to Telnet without buffering delays
- [ ] Telnet output displayed on stdout in real-time
- [ ] Graceful exit on Ctrl+C, Ctrl+D, or Ctrl+]
- [ ] Connection errors show helpful messages
- [ ] Session cleanup on abnormal termination
