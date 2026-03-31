---
wave: 1
depends_on: []
files_modified:
  - src/ensp_cli/services/device_launcher.py
  - src/ensp_cli/services/port_allocator.py
  - src/ensp_cli/services/mac_generator.py
  - src/ensp_cli/services/coordinate_allocator.py
autonomous: true
---

# Plan: Device Launcher Core

## Goal
Implement the core device launching infrastructure to start Huawei eNSP devices independently.

## Context

### Technical Findings
From research of user's eNSP v1.3 installation:

**Router Executable:**
- Path: `C:\Program Files\Huawei\eNSP\vboxserver\devices\AR\AR\eNSP_Router.exe`
- Parameters: `"sim" "system_mac=<mac>" "<device_name>"`
- Base Image: `AR_Base\AR_Base.vdi`

**Switch Executable:**
- Path: `C:\Program Files\Huawei\eNSP\vboxserver\devices\LSW\s5700\eNSP_Switch.exe`
- Parameters: Same as router
- Base Image: S5700 directory structure

**Device Models:**
- Routers: AR2220, AR3260
- Switches: S3700, S5700
- Firewalls: USG5500 (future)

### Port Allocation
- Default range: 2000-2100
- Scan for available ports
- Reserve port before launching
- **Detect GUI devices**: Scan `eNSP_Router.exe` / `eNSP_Switch.exe` processes to avoid conflicts

### MAC Address Format
- Huawei OUI: `54-89-98` (routers), `4C-1F-CC` (switches)
- Random last 3 bytes: `XX-XX-XX`
- Ensure uniqueness per device

### GUI Compatibility
- Detect existing GUI-launched devices via process scanning
- Coordinate port allocation to avoid conflicts
- Support "integration mode" where CLI can manage GUI devices
- Update `.topo` file to include CLI-launched devices (for GUI visibility)

## Tasks

<task id="1" name="Create MAC address generator">
Create `src/ensp_cli/services/mac_generator.py`.

Implementation:
1. Define `MacGenerator` class
2. Map device types to Huawei OUIs:
   - Router: 54-89-98
   - Switch: 4C-1F-CC
3. Generate random last 3 bytes
4. Track used MACs to avoid collisions
5. Format: `XX-XX-XX-XX-XX-XX`

<verify>
Generator produces valid unique MAC addresses.
</verify>
</task>

<task id="2" name="Create port allocator">
Create `src/ensp_cli/services/port_allocator.py`.

Implementation:
1. Define `PortAllocator` class
2. Default range: 2000-2100
3. **Detect GUI device ports**: Scan for eNSP_Router/Switch processes and extract their ports
4. Scan for available ports using socket.bind()
5. Exclude ports used by GUI devices
6. Reserve port (mark as in-use)
7. Release port on device stop
8. Thread-safe for concurrent allocation

<verify>
Allocator returns unique available ports, avoiding GUI conflicts.
</verify>
</task>

<task id="2b" name="Create coordinate allocator">
Create `src/ensp_cli/services/coordinate_allocator.py`.

Implementation:
1. Define `CoordinateAllocator` class
2. Parse existing topology to find device positions
3. Calculate bounding box of existing devices
4. Allocate new position with grid layout:
   - Default grid size: 100x100 pixels
   - Place to the right or below existing devices
   - Avoid overlap
5. Support custom x, y coordinates if specified
6. Return (cx, cy) tuple

<verify>
Allocator returns non-overlapping coordinates for new devices.
</verify>
</task>

<task id="3" name="Create device launcher service">
Create `src/ensp_cli/services/device_launcher.py`.

Implementation:
1. Define `DeviceLauncher` class
2. Map device models to executables:
   ```python
   DEVICE_EXECUTABLES = {
       "AR2220": ".../devices/AR/AR/eNSP_Router.exe",
       "AR3260": ".../devices/AR/AR/eNSP_Router.exe",
       "S3700": ".../devices/LSW/s3700/eNSP_Switch.exe",
       "S5700": ".../devices/LSW/s5700/eNSP_Switch.exe",
   }
   ```
3. Implement `launch_router(name, model, port=None)` method
4. Implement `launch_switch(name, model, port=None)` method
5. Build command line: `[exe, "sim", f"system_mac={mac}", name]`
6. Start process with subprocess
7. Return process info (PID, port, MAC)

<verify>
Launcher can start router and switch processes.
</verify>
</task>

<task id="4" name="Add device readiness detection">
Implement polling to detect when device is ready.

Implementation:
1. After process start, poll Telnet port
2. Try connecting every 1 second
3. Timeout after 30 seconds
4. **Auto-retry**: If launch fails, retry up to 3 times with 2s delay
5. Return ready status and time taken
6. Handle connection failures gracefully

<verify>
Detection accurately reports device readiness.
</verify>
</task>

<task id="5" name="Add tests for launcher components">
Create `tests/services/test_device_launcher.py`.

Tests:
1. Test MAC generator produces valid MACs
2. Test MAC generator avoids collisions
3. Test port allocator finds available ports
4. Test port allocator reserves/releases
5. Test launcher builds correct command line
6. Test readiness detection (mock)

<verify>
All tests pass with good coverage.
</verify>
</task>

## must_haves

Goal: Core device launching works reliably

- [ ] MAC generator produces unique valid addresses
- [ ] Port allocator finds and reserves available ports
- [ ] Can launch router process with correct parameters
- [ ] Can launch switch process with correct parameters
- [ ] Device readiness detection works
- [ ] Tests cover all components
