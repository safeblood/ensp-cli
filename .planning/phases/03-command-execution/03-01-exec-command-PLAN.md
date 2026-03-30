---
wave: 1
depends_on: []
files_modified:
  - src/ensp_cli/commands/exec.py
  - src/ensp_cli/cli/main.py
autonomous: true
---

# Plan: Implement Exec Command

## Goal
User can execute a single command on a device and return the output (EXEC-01).

## Context
Phase 2 established the Telnet connection layer with:
- `TelnetClient` with `write_line()`, `read_until()` methods
- `device_session` context manager for connection handling
- `VRP_PROMPT_ANY` regex pattern for prompt detection
- `console` command for interactive sessions

The `exec` command will reuse these components for non-interactive command execution.

## Tasks

<task id="1" name="Create exec command module">
Create `src/ensp_cli/commands/exec.py` with the async execution logic.

Implementation:
1. Import `device_session` from `connection_manager`
2. Import `VRP_PROMPT_ANY` from `telnet_client`
3. Import helper functions from `console.py` (find_topology_file, parse_topology, get_device_or_exit)
4. Create `execute_command()` async function that:
   - Connects to device using `device_session`
   - Reads initial banner/prompt using `read_until(VRP_PROMPT_ANY)`
   - Sends command using `write_line(command)`
   - Reads response until next prompt using `read_until(VRP_PROMPT_ANY)`
   - Strips command echo from beginning of output
   - Strips trailing prompt from output
   - Returns clean command output
5. Create `exec_async()` function that handles errors and returns exit code

Command echo stripping: Split output by newlines and remove first line if it matches the command.

<verify>
Module exists with `execute_command()` and `exec_async()` functions defined.
</verify>
</task>

<task id="2" name="Add exec Typer command with --output option">
Add Typer command with --output json option for CLI-01 compliance.

Command signature:
```python
@app.command(name="exec")
def exec_command(
    device_name: str = typer.Argument(..., help="Name of the device"),
    command: str = typer.Argument(..., help="Command to execute (quoted)"),
    topology: Optional[Path] = typer.Option(None, "--topology", "-t"),
    output: str = typer.Option("text", "--output", "-o", help="Output format"),
) -> None:
    """Execute a single command on a device and return output."""
Add the `exec` command to `src/ensp_cli/cli/main.py`.

Implementation:
1. Import the exec command from `ensp_cli.commands.exec`
2. Register command: `app.command(name="exec")(exec_command)`
3. The command should accept:
   - `device_name` (str, positional, required)
   - `command` (str, positional, required) - the command to execute
   - `--topology` / `-t` (Optional[Path], exists=True, dir_okay=False)
   - `--timeout` (float, default=10.0)
   - `--output` / `-o` (str, default="text") - "text" or "json"

Help text example:
```
Execute a single command on a device.

Examples:
    ensp-cli exec Router1 "display version"
    ensp-cli exec Router1 "display ip interface brief" --output json
    ensp-cli exec Router1 "system-view" --topology mylab.topo
```

<verify>
Command registered and appears in `ensp-cli --help` output.
</verify>
</task>

<task id="3" name="Implement text output formatting">
Implement text output formatting in exec command.

Implementation:
1. When `--output text` (default):
   - Print clean command output directly to stdout
   - No additional formatting or prefixes
2. Use `console.print()` for Rich compatibility

<verify>
Running `ensp-cli exec Router1 "display version"` prints the device output cleanly.
</verify>
</task>

<task id="4" name="Implement JSON output format">
Implement JSON output format in exec command.

Implementation:
1. When `--output json`:
   ```json
   {
     "status": "success",
     "device": "Router1",
     "command": "display version",
     "output": "<command output here>"
   }
   ```
2. On error:
   ```json
   {
     "status": "error",
     "error": "error message"
   }
   ```

<verify>
Running `ensp-cli exec Router1 "display version" --output json` returns valid JSON.
</verify>
</task>

<task id="5" name="Add exit code handling">
Implement proper exit codes for the exec command.

Exit codes:
- 0: Success (command executed and output returned)
- 1: General error (device not found, connection failed, etc.)
- 2: File not found (topology file)
- 3: Parse error (invalid topology file)
- 5: Command timeout (device didn't respond within timeout)

Implementation:
- Use `raise typer.Exit(code)` pattern consistent with existing commands
- Return exit codes from `exec_async()` and raise in command function

<verify>
- `ensp-cli exec ExistingRouter "cmd"; echo $?` returns 0
- `ensp-cli exec NonExistentRouter "cmd"; echo $?` returns 1
</verify>
</task>

<task id="6" name="Write tests for exec command">
Add tests for the exec command.

Test file: `tests/commands/test_exec.py`

Tests to add:
1. Test `execute_command()` strips command echo correctly
2. Test `execute_command()` strips trailing prompt
3. Test `exec_async()` returns correct exit code on success
4. Test `exec_async()` returns exit code 1 on connection error
5. Test JSON output format is valid
6. Test command timeout handling

Use mocking for TelnetClient to avoid requiring actual device connections.

<verify>
All new tests pass with `pytest tests/commands/test_exec.py -v`.
</verify>
</task>

## must_haves

Goal: User can execute a single command on a device and return the output (EXEC-01)

- [ ] `ensp-cli exec <device> "<command>"` connects to device and executes command
- [ ] Command output is displayed (without command echo or prompt)
- [ ] `--output json` returns structured JSON with status, device, command, output
- [ ] Exit code 0 on success, non-zero on failure
- [ ] Tests cover command execution and output parsing
