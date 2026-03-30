# Phase 4: Device Operations

**Goal:** Enable topology modification - add/remove devices and manage connections

**Requirements Mapped:**
| Requirement | Description |
|-------------|-------------|
| TOPO-03 | Add new devices to topology |
| TOPO-04 | Remove devices from topology |
| TOPO-05 | Create connections between devices |
| TOPO-06 | Delete connections between devices |

**Success Criteria:**
1. User can add a new device with `ensp-cli add-device <name> --type <type>`
2. User can remove a device with `ensp-cli remove-device <name>`
3. User can connect two devices with `ensp-cli connect <dev1> <dev2> --port1 <p1> --port2 <p2>`
4. User can disconnect devices with `ensp-cli disconnect <dev1> <dev2>`
5. Changes are saved back to the .topo file
6. Visual output reflects changes immediately

---

## Sub-Plans

### 04-01: Add/Remove Device Commands
**Goal:** Implement device addition and removal

**Tasks:**
1. Create `add-device` command with device type selection
2. Create `remove-device` command with confirmation
3. Implement topology modification logic
4. Add save functionality to write back to .topo file

**must_haves:**
- [ ] `ensp-cli add-device` creates new device with unique name
- [ ] `ensp-cli remove-device` removes device and its connections
- [ ] Changes persist to .topo file

### 04-02: Connect/Disconnect Commands  
**Goal:** Implement connection management

**Tasks:**
1. Create `connect` command to link two devices
2. Create `disconnect` command to remove links
3. Validate interface availability
4. Update connection visualization

**must_haves:**
- [ ] `ensp-cli connect` creates valid connection
- [ ] `ensp-cli disconnect` removes connection
- [ ] Interface conflict detection

### 04-03: Topology Save/Backup
**Goal:** Ensure changes are persisted safely

**Tasks:**
1. Implement topology serialization to XML
2. Add backup before modification
3. Add rollback on error
4. Validate saved topology

**must_haves:**
- [ ] Changes saved to .topo file
- [ ] Backup created before modification
- [ ] Rollback on save failure

---

## Execution Waves

| Wave | Plans | Description |
|------|-------|-------------|
| 1 | 04-01, 04-02, 04-03 | All sub-plans can execute in parallel (autonomous) |

## Plan Files

- **04-01-add-remove-device-PLAN.md** - Add/remove device commands
- **04-02-connect-disconnect-PLAN.md** - Connect/disconnect commands
- **04-03-topology-save-PLAN.md** - Topology save/backup

## Status

**Phase 4 Status:** 🔵 Planned  
**Dependencies:** Phase 1-3 (complete)  
**Ready for:** Execution

*Created: 2026-03-30*
*Updated: 2026-03-30 with detailed plans*
