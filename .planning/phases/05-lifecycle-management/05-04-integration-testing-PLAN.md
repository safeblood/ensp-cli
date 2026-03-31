---
wave: 3
depends_on: ["05-01-device-launcher-PLAN.md", "05-02-process-manager-PLAN.md", "05-03-cli-commands-PLAN.md"]
files_modified:
  - tests/services/test_device_launcher.py
  - tests/commands/test_lifecycle.py
  - tests/integration/test_device_lifecycle.py
autonomous: true
---

# Plan: Integration and Testing

## Goal
Ensure reliable operation with comprehensive test coverage.

## Context
Integration testing validates that all components work together correctly.

## Tasks

<task id="1" name="Add integration tests for launch-stop cycle">
Create `tests/integration/test_device_lifecycle.py`.

Tests:
1. Test launch router -> verify running -> stop -> verify stopped
2. Test launch switch -> verify running -> stop -> verify stopped
3. Test launch multiple devices concurrently
4. Test port conflict handling
5. Test MAC collision avoidance

<verify>
All lifecycle tests pass.
</verify>
</task>

<task id="2" name="Add port conflict tests">
Test port allocation edge cases.

Tests:
1. Test port already in use by other app
2. Test port range exhausted
3. Test port release after stop
4. Test concurrent port allocation (thread safety)

<verify>
Port conflicts handled gracefully.
</verify>
</task>

<task id="2b" name="Add coordinate allocator tests">
Test coordinate allocation for topology positioning.

Tests:
1. Test coordinate calculation from existing topology
2. Test non-overlapping position allocation
3. Test grid layout algorithm
4. Test custom coordinate override (--x, --y)
5. Test boundary conditions (empty topology)

<verify>
Coordinates allocated correctly without overlap.
</verify>
</task>

<task id="3" name="Add readiness timeout tests">
Test device startup failure scenarios.

Tests:
1. Test device that never becomes ready
2. Test timeout handling
3. Test cleanup after failed launch
4. Test error messages

<verify>
Timeout and error handling works.
</verify>
</task>

<task id="4" name="Add topology launch tests">
Test batch device launching.

Tests:
1. Test launch-topology with mixed devices
2. Test parallel vs sequential launch
3. Test partial failure handling
4. Test progress reporting

<verify>
Topology launch works reliably.
</verify>
</task>

<task id="5" name="Add CLI command tests">
Create `tests/commands/test_lifecycle.py`.

Tests:
1. Test launch-router command with mocks
2. Test launch-switch command with mocks
3. Test stop-device command
4. Test ps command output formats
5. Test launch-topology command
6. Test error handling and exit codes

<verify>
All CLI tests pass.
</verify>
</task>

<task id="6" name="Add documentation">
Update documentation for Phase 5.

Documentation:
1. Update README.md with new commands
2. Add examples for launch/stop/ps
3. Document device model mappings
4. Add troubleshooting guide

<verify>
Documentation complete and accurate.
</verify>
</task>

<task id="7" name="Create SUMMARY.md">
Create `05-04-integration-testing-SUMMARY.md`.

Contents:
- Test coverage report
- All success criteria verified
- Known limitations
- Usage examples

<verify>
Summary complete.
</verify>
</task>

## must_haves

Goal: Phase 5 is production-ready

- [x] 90%+ test coverage
- [x] All success criteria pass
- [x] Integration tests validate full workflows
- [x] Coordinate allocator tests pass
- [x] Topology coordinate updates verified
- [x] Documentation complete
- [x] No critical or major bugs
- [x] Performance acceptable (devices start in <30s)

## Status

**Completed:** 2026-03-31  
**Total Tests:** 84 passing  
**Test Files:**
- tests/services/test_device_launcher.py (25 tests)
- tests/services/test_process_manager.py (16 tests)
- tests/integration/test_device_lifecycle.py (23 tests)
- tests/commands/test_lifecycle.py (20 tests)
