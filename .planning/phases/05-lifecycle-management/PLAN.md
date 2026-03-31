# Phase 5: Device Lifecycle Management

**Goal:** Enable independent device launching and management without eNSP GUI

**Status:** 🔵 Planned  
**Dependencies:** Phase 1-4 (complete)  

---

## Background

### Research Summary

Through investigation of the user's eNSP installation, we discovered:

| Finding | Detail |
|---------|--------|
| **eNSP Version** | v1.3.x (2018/12/19) |
| **Virtualization** | Huawei lightweight engine (not QEMU) |
| **Router Process** | `eNSP_Router.exe` in `sim` mode |
| **Switch Process** | `eNSP_Switch.exe` in `sim` mode |
| **Base Images** | `.vdi` format (VirtualBox-based) |
| **Console Ports** | TCP ports 2000, 2001, ... |
| **MAC Address** | Required per device (`system_mac=XX-XX-XX-XX-XX-XX`) |

### Actual Running Commands

**Router (R2):**
```
"C:\Program Files\Huawei\eNSP\vboxserver\devices\AR\AR\eNSP_Router.exe" 
"sim" "system_mac=54-89-98-EB-37-AE" "R2"
```

**Switch (LSW2):**
```
"C:\Program Files\Huawei\eNSP\vboxserver\devices\LSW\s5700\eNSP_Switch.exe" 
"sim" "system_mac=4C-1F-CC-95-5A-B0" "LSW2"
```

---

## Requirements Mapped

| ID | Requirement | Description |
|----|-------------|-------------|
| LIFECYCLE-01 | Launch router devices | Start AR2220/AR3260 routers independently |
| LIFECYCLE-02 | Launch switch devices | Start S3700/S5700 switches independently |
| LIFECYCLE-03 | Stop running devices | Gracefully terminate device processes |
| LIFECYCLE-04 | View device status | List running devices with ports and PIDs |
| LIFECYCLE-05 | Topology launch | Start all devices defined in .topo file |
| LIFECYCLE-06 | Auto port assignment | Automatically assign available console ports |

---

## Success Criteria

1. [ ] `ensp-cli launch-router R1 --model AR2220` starts router device
2. [ ] `ensp-cli launch-switch S1 --model S5700` starts switch device
3. [ ] `ensp-cli stop-device R1` terminates device process
4. [ ] `ensp-cli ps` shows running devices with ports and status (both CLI and GUI)
5. [ ] `ensp-cli launch-topology lab.topo` starts all devices in topology
6. [ ] Console ports auto-assigned without conflicts (detects GUI devices)
7. [ ] Devices reachable via Telnet within 30 seconds of launch
8. [ ] `.topo` file updated with CLI-launched devices **including coordinates (cx, cy)**
9. [ ] Launch retries 3 times on failure before giving up
10. [ ] Max 10 devices by default (configurable)
11. [ ] **Devices appear at proper positions in GUI (no overlap, grid layout)**
12. [ ] **Custom coordinates supported via `--x` and `--y` parameters**

---

## Sub-Plans

### 05-01: Device Launcher Core
**Goal:** Implement device launching infrastructure

**Tasks:**
1. Create `DeviceLauncher` service class
2. Implement MAC address generator (Huawei OUI: 54-89-98, 4C-1F-CC)
3. Implement port allocator (scan 2000-2100)
4. Create process wrapper for eNSP_Router.exe / eNSP_Switch.exe
5. Add device readiness detection (Telnet polling)

**Must-Haves:**
- [ ] Can launch router with correct parameters
- [ ] Can launch switch with correct parameters
- [ ] MAC addresses are unique
- [ ] Ports are allocated without conflict

### 05-02: Process Management
**Goal:** Track and manage running device processes

**Tasks:**
1. Create `ProcessManager` service
2. Implement running state persistence (JSON file)
3. Add process monitoring (PID tracking)
4. Implement graceful stop (SIGTERM equivalent on Windows)
5. Add force kill option for hung processes

**Must-Haves:**
- [ ] Can list running devices with PIDs
- [ ] Can stop device by name
- [ ] State persists across CLI invocations
- [ ] Handles process crashes gracefully

### 05-03: CLI Commands
**Goal:** Add launch/stop/status commands to CLI

**Tasks:**
1. Implement `launch-router` command
2. Implement `launch-switch` command
3. Implement `stop-device` command
4. Implement `ps` command (list running)
5. Implement `launch-topology` command

**Commands:**
```bash
ensp-cli launch-router R1 --model AR2220 [--port 2000]
ensp-cli launch-switch S1 --model S5700 [--port 2001]
ensp-cli stop-device R1 [--force]
ensp-cli ps [--output json]
ensp-cli launch-topology lab.topo [--timeout 60]
```

**Must-Haves:**
- [ ] All commands work with proper error handling
- [ ] Help text and examples
- [ ] JSON output support

### 05-04: Integration & Testing
**Goal:** Ensure reliable operation and test coverage

**Tasks:**
1. Add integration tests for launch/stop cycle
2. Test port conflict handling
3. Test multiple device launch
4. Test topology launch
5. Add readiness timeout handling

**Must-Haves:**
- [ ] 90%+ test coverage
- [ ] All success criteria pass
- [ ] Documentation complete

---

## Execution Waves

| Wave | Plans | Description |
|------|-------|-------------|
| 1 | 05-01 | Device launcher core (foundational) |
| 2 | 05-02 | Process management (depends on 05-01) |
| 3 | 05-03, 05-04 | CLI commands and testing (parallel) |

---

## Plan Files

- **05-01-device-launcher-PLAN.md** - Device launcher core
- **05-02-process-manager-PLAN.md** - Process management
- **05-03-cli-commands-PLAN.md** - CLI command implementation
- **05-04-integration-testing-PLAN.md** - Integration and testing

---

## Status

**Phase 5 Status:** 🔵 Planned  
**Research:** Complete (see findings above)  
**Ready for:** Planning sub-phases and execution

*Created: 2026-03-31 after eNSP virtualization research*
