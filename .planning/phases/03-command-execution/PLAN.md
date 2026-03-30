# Phase 3: Command Execution & CLI Polish

**Goal:** Enable command execution and complete CLI functionality

**Requirements Mapped:**
| Requirement | Description |
|-------------|-------------|
| EXEC-01 | Execute a single command on a device and return the output |
| CLI-01 | All commands support `--output json` for machine-readable output |
| CLI-02 | CLI provides help documentation and version flags |
| CLI-03 | CLI returns appropriate exit codes (0=success, non-zero=failure) |

---

## Overview

Phase 3 consists of three parallel workstreams executed in Wave 1:

1. **03-01: Exec Command** - Non-interactive command execution on devices
2. **03-02: Output Formatting** - Rich syntax highlighting and consistent JSON output
3. **03-03: CLI Polish** - Help documentation, version flags, and exit codes

All workstreams are autonomous (no dependencies between them) and were executed together.

---

## Plan 03-01: Implement Exec Command

**Goal:** User can execute a single command on a device and return the output (EXEC-01)

**Files Modified:**
- `src/ensp_cli/commands/exec.py` (created)
- `src/ensp_cli/cli/main.py` (modified)
- `tests/commands/test_exec.py` (created)

**Key Tasks:**
1. Create exec command module with `execute_command()` and `exec_async()`
2. Add Typer command with `--output` option
3. Implement text and JSON output formatting
4. Add exit code handling (0, 1, 2, 3, 5)
5. Write comprehensive tests

**must_haves:**
- [x] `ensp-cli exec <device> "<command>"` connects to device and executes command
- [x] Command output is displayed (without command echo or prompt)
- [x] `--output json` returns structured JSON with status, device, command, output
- [x] Exit code 0 on success, non-zero on failure
- [x] Tests cover command execution and output parsing

---

## Plan 03-02: Output Formatting with Rich

**Goal:** Command output has proper formatting and syntax highlighting (CLI-01 enhancement)

**Files Modified:**
- `src/ensp_cli/output.py` (created)
- `src/ensp_cli/commands/exec.py` (modified)
- `src/ensp_cli/commands/console.py` (modified)
- `src/ensp_cli/cli/main.py` (modified)
- `tests/test_output.py` (created)

**Key Tasks:**
1. Create output utility module with `OutputFormat` enum
2. Add `output_json()`, `output_text()`, `output_error()` utilities
3. Add Rich Syntax highlighting using "cisco" lexer
4. Refactor all commands to use shared output utilities
5. Add tests for output formatting

**must_haves:**
- [x] `ensp-cli exec` output is syntax-highlighted using Rich Syntax
- [x] All commands (`list`, `console`, `exec`) support `--output json`
- [x] JSON output format is consistent across all commands
- [x] Shared output utilities module reduces code duplication
- [x] Error messages use consistent formatting

---

## Plan 03-03: CLI Polish

**Goal:** CLI provides comprehensive help documentation, version information, and consistent exit codes (CLI-02, CLI-03)

**Files Modified:**
- `src/ensp_cli/cli/main.py` (modified)
- `src/ensp_cli/commands/console.py` (modified)
- `src/ensp_cli/commands/exec.py` (modified)
- `tests/test_cli_interface.py` (created)
- `README.md` (modified)

**Key Tasks:**
1. Enhance main CLI help with rich markup and examples
2. Add exit code documentation to all command docstrings
3. Audit exit code consistency across all commands
4. Verify version consistency
5. Write integration tests for CLI interface
6. Document exit codes in README

**must_haves:**
- [x] `ensp-cli --help` shows rich formatted help with examples and exit codes
- [x] `ensp-cli --version` prints version and exits with code 0
- [x] Each command's `--help` shows command-specific exit codes
- [x] Exit codes are consistent across all commands
- [x] All commands use `raise typer.Exit(code)` pattern
- [x] Integration tests verify exit codes
- [x] README documents exit codes

---

## Execution Waves

| Wave | Plans | Description |
|------|-------|-------------|
| 1 | 03-01, 03-02, 03-03 | All workstreams executed in parallel (autonomous, no dependencies) |

---

## Success Criteria

1. ✅ User can run `ensp-cli exec <device-name> "<command>"` and see the command output
2. ✅ User can use `--output json` on any command to get structured, machine-readable output
3. ✅ User can run `ensp-cli --help` to see available commands and `ensp-cli --version` to see version
4. ✅ User can check exit code (`$?` or `%ERRORLEVEL%`) to determine if a command succeeded (0) or failed (non-zero)
5. ✅ User receives command output with proper formatting and syntax highlighting in terminal

---

## Exit Codes Reference

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (device not found, connection failed) |
| 2 | File not found |
| 3 | Invalid XML / Parse error |
| 4 | Permission denied |
| 5 | Command timeout |

---

## Status

**Phase 3 is COMPLETE** ✅

- All 3 sub-plans executed successfully
- All 17 must_haves delivered (5 + 5 + 7)
- All 5 success criteria met
- 173 tests passing

*Last updated: 2026-03-30*
