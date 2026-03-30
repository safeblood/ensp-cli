---
wave: 1
depends_on: []
files_modified:
  - src/ensp_cli/cli/main.py
  - src/ensp_cli/commands/exec.py
  - src/ensp_cli/commands/console.py
autonomous: true
---

# Plan: Output Formatting with Rich

## Goal
Command output has proper formatting and syntax highlighting in terminal (CLI-01 enhancement).

## Context
The project already uses Rich for table output. This plan adds:
1. Syntax highlighting for device command output (VRP/CLI commands)
2. Consistent `--output json` support across ALL commands
3. Proper console output handling

## Tasks

<task id="1" name="Add Rich Syntax highlighting for exec output">
Add syntax highlighting to exec command output.

Implementation in `src/ensp_cli/commands/exec.py`:
1. Import `Syntax` from `rich.syntax`
2. When `--output text`, wrap device output in Syntax:
   ```python
   from rich.syntax import Syntax
   
   syntax = Syntax(
       output,
       "cisco",  # Closest lexer for VRP CLI output
       theme="monokai",
       line_numbers=False,
       word_wrap=True,
   )
   console.print(syntax)
   ```
3. Use "cisco" lexer (Pygments has no VRP-specific lexer, but Cisco IOS is similar)
4. Fall back to plain text if Syntax fails

<verify>
Running `ensp-cli exec Router1 "display version"` shows syntax-highlighted output.
</verify>
</task>

<task id="2" name="Add global output format option to main CLI">
Ensure all commands support `--output json` consistently.

Implementation in `src/ensp_cli/cli/main.py`:
1. Review existing `list` command JSON output - already implemented
2. Review `console` command JSON output - already implemented
3. Ensure `exec` command JSON output follows same pattern

JSON format consistency:
- Success: `{ "status": "success", ...command-specific fields }`
- Error: `{ "status": "error", "error": "message" }`

<verify>
All commands (`list`, `console`, `exec`) support `--output json` with consistent format.
</verify>
</task>

<task id="3" name="Update console command with output option documentation">
Ensure console command documents its `--output` option consistently.

Implementation in `src/ensp_cli/commands/console.py`:
1. Verify `--output json` is documented in help text
2. Verify JSON output format matches standard pattern
3. Update help examples if needed

Current JSON output:
```json
{
  "status": "connected",
  "device": "Router1",
  "address": "127.0.0.1:5000",
  "device_type": "Router",
  "model": "AR2220"
}
```

<verify>
Console command help shows `--output` option with json choice.
</verify>
</task>

<task id="4" name="Add output utility module">
Create reusable output formatting utilities.

Create `src/ensp_cli/output.py`:

```python
"""Output formatting utilities for CLI commands."""

import json
from enum import Enum
from typing import Any

from rich.console import Console
from rich.syntax import Syntax

console = Console()


class OutputFormat(str, Enum):
    """Output format options."""
    TEXT = "text"
    JSON = "json"


def output_json(data: dict[str, Any]) -> None:
    """Output data as JSON."""
    print(json.dumps(data, indent=2))


def output_text(data: str, lexer: str = "cisco") -> None:
    """Output text with syntax highlighting."""
    try:
        syntax = Syntax(
            data,
            lexer,
            theme="monokai",
            line_numbers=False,
            word_wrap=True,
        )
        console.print(syntax)
    except Exception:
        # Fallback to plain text
        print(data)


def output_error(message: str, output_format: OutputFormat) -> None:
    """Output error message."""
    if output_format == OutputFormat.JSON:
        print(json.dumps({"status": "error", "error": message}))
    else:
        console.print(f"[red]Error: {message}[/red]")
```

<verify>
Module created with all utility functions.
</verify>
</task>

<task id="5" name="Refactor existing commands to use output utilities">
Update existing commands to use the new output utilities.

Changes:
1. Update `src/ensp_cli/cli/main.py`:
   - Import `OutputFormat` from `output` module
   - Update `list` command to use shared `OutputFormat`
   - Use `output_json` and `output_text` utilities

2. Update `src/ensp_cli/commands/exec.py`:
   - Use `output_text` for text output with syntax highlighting
   - Use `output_json` for JSON output
   - Use `output_error` for error messages

3. Update `src/ensp_cli/commands/console.py`:
   - Use `output_json` for JSON output

<verify>
All commands use shared output utilities; no duplicate JSON formatting code.
</verify>
</task>

<task id="6" name="Add tests for output formatting">
Add tests for output formatting utilities.

Test file: `tests/test_output.py`

Tests to add:
1. Test `output_json()` produces valid JSON
2. Test `output_text()` produces syntax-highlighted output
3. Test `output_error()` produces correct JSON error format
4. Test `output_error()` produces correct text error format
5. Test fallback to plain text when Syntax fails

<verify>
All output utility tests pass.
</verify>
</task>

## must_haves

Goal: Command output has proper formatting and syntax highlighting

- [ ] `ensp-cli exec` output is syntax-highlighted using Rich Syntax
- [ ] All commands (`list`, `console`, `exec`) support `--output json`
- [ ] JSON output format is consistent across all commands
- [ ] Shared output utilities module reduces code duplication
- [ ] Error messages use consistent formatting
