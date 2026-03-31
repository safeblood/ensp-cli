---
wave: 2
depends_on: ["05-01-device-launcher-PLAN.md"]
files_modified:
  - src/ensp_cli/services/process_manager.py
  - src/ensp_cli/models/running_device.py
autonomous: true
---

# Plan: Process Management

## Goal
Track and manage running device processes with persistence.

## Context
Devices are launched as independent Windows processes. We need to:
1. Track which devices are running
2. Store process IDs (PIDs) for management
3. Persist state across CLI invocations
4. Support graceful and forceful stop
5. Detect crashed or hung processes

## Tasks

<task id="1" name="Create RunningDevice model">
Create `src/ensp_cli/models/running_device.py`.

Implementation:
1. Define `RunningDevice` Pydantic model:
   ```python
   class RunningDevice(BaseModel):
       name: str                    # Device name
       device_type: str             # router/switch/firewall
       model: str                   # AR2220, S5700, etc.
       pid: int                     # Windows process ID
       port: int                    # Console port
       mac_address: str             # Assigned MAC
       status: str                  # starting/running/stopped/error
       started_at: datetime         # Launch timestamp
       workspace: Optional[Path]    # Working directory
   ```
2. Add validation
3. Add methods for status transitions

<verify>
Model validates and serializes correctly.
</verify>
</task>

<task id="2" name="Create process manager service">
Create `src/ensp_cli/services/process_manager.py`.

Implementation:
1. Define `ProcessManager` class
2. State file location: `.ensp/state/running_devices.json`
3. Methods:
   - `register_device(device: RunningDevice)` - Add to tracking
   - `unregister_device(name: str)` - Remove from tracking
   - `get_device(name: str)` - Get device info
   - `list_devices()` - List all running
   - `stop_device(name: str, force=False)` - Stop process
   - `refresh_status()` - Update all device statuses
4. Handle state file read/write

<verify>
Manager persists and retrieves device state.
</verify>
</task>

<task id="3" name="Implement graceful stop">
Implement process termination logic.

Implementation:
1. Graceful stop:
   - Try sending Ctrl+C or Ctrl+Break
   - Wait up to 5 seconds
   - Check if process terminated
2. Force stop (if graceful fails or force=True):
   - Use `taskkill /F /PID {pid}` on Windows
   - Or `process.terminate()` then `process.kill()`
3. Update device status to "stopped"
4. Release allocated port
5. Clean up state file

<verify>
Can stop devices gracefully and forcefully.
</verify>
</task>

<task id="4" name="Add process monitoring">
Detect crashed or hung processes.

Implementation:
1. `refresh_status()` method:
   - Check if PID still exists
   - Verify process is eNSP_Router/Switch
   - Update status if process died
   - Clean up orphaned entries
2. Handle stale state (process died externally)
3. Auto-cleanup on list operation

<verify>
Accurately detects process status changes.
</verify>
</task>

<task id="5" name="Add process manager tests">
Create `tests/services/test_process_manager.py`.

Tests:
1. Test device registration/unregistration
2. Test state persistence (save/load)
3. Test graceful stop (mock)
4. Test force stop (mock)
5. Test status refresh
6. Test stale process cleanup

<verify>
All tests pass with good coverage.
</verify>
</task>

## must_haves

Goal: Process state is tracked and manageable

- [ ] RunningDevice model works
- [ ] State persists to JSON file
- [ ] Can stop devices gracefully
- [ ] Can force stop hung devices
- [ ] Status monitoring works
- [ ] Tests cover all scenarios
