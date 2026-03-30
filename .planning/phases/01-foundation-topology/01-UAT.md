# Phase 1 - User Acceptance Testing

**Started:** 2026-03-30
**Status:** in_progress

## Tests

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 1 | `ensp-cli --version` shows version | Version number displayed (e.g., "ensp-cli 0.1.0") | ✓ pass | |
| 2 | `ensp-cli list <valid.topo>` displays device table | Rich table with Name, Type, Model, Console Port columns | ✓ pass | |
| 3 | `ensp-cli list <file> --output json` produces valid JSON | Parseable JSON with devices and connections arrays | ✓ pass | |
| 4 | `ensp-cli list <file> --show-connections` shows links | Table with From Device, From Port, To Device, To Port | ✓ pass | Fixed - now correctly parses srcDeviceID/destDeviceID
| 5 | `ensp-cli list <nonexistent>` shows error + exit code | Clear error message, returns non-zero exit code | pending | |

## Issues Found

1. **Parser bug - Connection XML attributes** (FIXED)
   - Parser looked for `from_device`/`to_device` attributes
   - eNSP XML uses `srcDeviceID`/`destDeviceID` attributes
   - Also extracts interface info from `<interfacePair>` child elements
   - **Fix:** Updated `_parse_connections()` to use correct attribute names

---
*UAT session for phase 1*
