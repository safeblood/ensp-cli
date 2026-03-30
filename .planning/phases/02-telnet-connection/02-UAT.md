# Phase 2 - User Acceptance Testing

**Started:** 2026-03-30
**Status:** in_progress

## Tests

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 1 | `ensp-cli console --help` shows help | Help text with device_name argument and --topology, --output options | ✓ pass | |
| 2 | `ensp-cli console NonExistent --topology <file>` shows error | "Error: Device 'NonExistent' not found" + available devices list | ✓ pass | Lists LSW2, Cloud1, R2
| 3 | `ensp-cli console NonExistent --topology <file> --output json` | JSON error with available_devices array | ✓ pass | Fixed - JSON output now correct
| 4 | `ensp-cli console R2 --topology <file>` attempts connection | "Connected to R2 at 127.0.0.1:2000" + session start | ✓ pass | Connection works |
| 5 | Topology auto-discovery works | Find .topo file in current directory automatically | pending | |

## Issues Found

1. **JSON error output not working** (FIXED)
   - `get_device_or_exit()` printed text error before checking output_format
   - **Fix:** Pass output_format to get_device_or_exit(), handle JSON there

2. **Interactive session - command input not working** (ISSUE)
   - Connected successfully but user cannot type commands
   - Windows Terminal + PowerShell 中 msvcrt.getch() 工作不正常
   - **Status:** Needs fix - 考虑使用 sys.stdin.buffer.read() 替代

---
*UAT session for phase 2*
