---
wave: 1
depends_on: []
files_modified:
  - src/ensp_cli/cli/main.py
  - src/ensp_cli/__init__.py
  - pyproject.toml
autonomous: true
---

# Plan: CLI Polish - Help, Version, Exit Codes

## Goal
CLI provides comprehensive help documentation, version information, and consistent exit codes (CLI-02, CLI-03).

## Context
Typer provides built-in `--help` support. The project already has:
- `--version` flag working via `version_callback`
- Exit codes documented in main callback docstring
- Basic help for each command

This plan enhances help documentation and verifies exit code consistency.

## Tasks

<task id="1" name="Enhance main CLI help documentation">
Improve the main CLI help text with more comprehensive documentation.

Implementation in `src/ensp_cli/cli/main.py`:

1. Update the `app = typer.Typer()` instantiation:
```python
app = typer.Typer(
    name="ensp-cli",
    help="CLI tool for managing eNSP topology files and device connections",
    no_args_is_help=True,
    rich_markup_mode="rich",
    epilog="""
[bold]Examples:[/bold]
  ensp-cli list topology.topo
  ensp-cli console Router1
  ensp-cli exec Router1 "display version"

[bold]Exit Codes:[/bold]
  0 - Success
  1 - General error
  2 - File not found
  3 - Invalid XML / Parse error
  4 - Permission denied
  5 - Command timeout

For more information, visit: https://github.com/user/ensp-cli
"""
)
```

2. Ensure all commands have detailed docstrings with examples

<verify>
Running `ensp-cli --help` shows rich formatted help with examples and exit codes.
</verify>
</task>

<task id="2" name="Verify --version flag works correctly">
Verify and enhance the `--version` flag behavior.

Implementation:
1. Check current `version_callback` in `main.py` - should already work
2. Ensure version is read from `ensp_cli.__version__`
3. Version format: `ensp-cli version X.Y.Z`

Current implementation verification:
```python
def version_callback(value: bool) -> None:
    if value:
        console.print(f"ensp-cli version {__version__}")
        raise typer.Exit()
```

<verify>
Running `ensp-cli --version` prints version and exits with code 0.
</verify>
</task>

<task id="3" name="Document exit codes in command help">
Add exit code documentation to each command's help text.

Implementation:

1. Update `list` command docstring:
```python
def list(
    ...
) -> None:
    """List devices in a topology file.
    
    Exit codes:
        0: Success
        2: File not found
        3: Parse error
        4: Permission denied
    """
```

2. Update `console` command docstring in `commands/console.py`:
```python
def console_command(
    ...
) -> None:
    """Open an interactive console session with a device.
    
    Exit codes:
        0: Success or user disconnect
        1: Connection error or device not found
        2: Topology file not found
    """
```

3. Update `exec` command docstring in `commands/exec.py`:
```python
def exec_command(
    ...
) -> None:
    """Execute a single command on a device.
    
    Exit codes:
        0: Success
        1: Connection error or device not found
        2: Topology file not found
        3: Parse error
        5: Command timeout
    """
```

<verify>
Each command's help (`ensp-cli <command> --help`) shows exit codes.
</verify>
</task>

<task id="4" name="Audit and fix exit code consistency">
Audit all commands for exit code consistency and fix any issues.

Implementation:

1. Review current exit codes in `main.py`:
   - `list` command: Uses codes 1, 2, 3, 4 ✓
   - Main callback: Documents codes 0-4 ✓

2. Review `console` command in `commands/console.py`:
   - `console_async()` returns exit codes
   - Command raises `typer.Exit(exit_code)` ✓
   - Verify: Exit code 1 on connection error
   - Verify: Exit code 0 on success/disconnect

3. Review `exec` command (from Plan 03-01):
   - Exit code 0: Success
   - Exit code 1: General error (device not found, connection failed)
   - Exit code 2: File not found
   - Exit code 3: Parse error
   - Exit code 5: Command timeout

4. Ensure all commands use `raise typer.Exit(code)` pattern:
   - [ ] `list` command uses raise pattern
   - [ ] `console` command uses raise pattern
   - [ ] `exec` command uses raise pattern

<verify>
All commands consistently use `raise typer.Exit(code)` for exit codes.
</verify>
</task>

<task id="5" name="Add version to pyproject.toml consistency check">
Ensure version is consistent between `__init__.py` and `pyproject.toml`.

Implementation:
1. Check `pyproject.toml` for version
2. Check `src/ensp_cli/__init__.py` for `__version__`
3. If inconsistent, update `__init__.py` to match `pyproject.toml`

<verify>
Version in `__init__.py` matches version in `pyproject.toml`.
</verify>
</task>

<task id="6" name="Write integration tests for CLI interface">
Add integration tests for CLI help, version, and exit codes.

Test file: `tests/test_cli_interface.py`

Tests to add:
1. Test `--help` returns exit code 0
2. Test `--version` returns exit code 0 and prints version
3. Test `list --help` shows exit codes in help text
4. Test `console --help` shows exit codes in help text
5. Test `exec --help` shows exit codes in help text
6. Test each command returns correct exit code on error:
   - `list nonexistent.topo` returns 2
   - `console nonexistent_device` returns 1
   - `exec nonexistent_device "cmd"` returns 1

Use Typer's `CliRunner` for testing:
```python
from typer.testing import CliRunner
from ensp_cli.cli.main import app

runner = CliRunner()

result = runner.invoke(app, ["--version"])
assert result.exit_code == 0
assert "ensp-cli version" in result.output
```

<verify>
All CLI interface tests pass.
</verify>
</task>

<task id="7" name="Add README section for exit codes">
Document exit codes in project README.

Update `README.md`:
```markdown
## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (device not found, connection failed) |
| 2 | File not found |
| 3 | Invalid XML / Parse error |
| 4 | Permission denied |
| 5 | Command timeout |
```

<verify>
README.md contains exit codes section.
</verify>
</task>

## must_haves

Goal: CLI provides help documentation, version flags, and appropriate exit codes (CLI-02, CLI-03)

- [ ] `ensp-cli --help` shows rich formatted help with examples and exit codes
- [ ] `ensp-cli --version` prints version and exits with code 0
- [ ] Each command's `--help` shows command-specific exit codes
- [ ] Exit codes are consistent across all commands
- [ ] All commands use `raise typer.Exit(code)` pattern
- [ ] Integration tests verify exit codes
- [ ] README documents exit codes
