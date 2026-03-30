# Phase 4: Device Operations (Read-Only Helpers)

**Goal:** Provide read-only helper commands for device configuration viewing, export, and comparison

**Note:** Phase 4 was redefined from "topology modification" (add/remove devices, connections) to "read-only helpers" because:
- eNSP does not watch .topo file changes
- Modified topology requires manual intervention in eNSP GUI
- Read-only operations are immediately useful without GUI interaction

**Requirements Mapped:**
| Requirement | Description |
|-------------|-------------|
| TOPO-03 | Add new devices to topology → CHANGED to: View device configuration |
| TOPO-04 | Remove devices from topology → CHANGED to: Export device configuration |
| TOPO-05 | Create connections between devices → CHANGED to: Compare configurations |
| TOPO-06 | Delete connections between devices → CHANGED to: Audit configuration consistency |

**Success Criteria:**
1. User can view device configuration with `ensp-cli show-config <device>`
2. User can export config with `ensp-cli export-config <device> -o <file>`
3. User can import config with `ensp-cli import-config <device> <file>`
4. User can compare configs with `ensp-cli diff-config <dev1> <dev2>`
5. User can audit all configs with `ensp-cli audit-configs`
6. JSON output supported for automation/integration
7. All commands include tests

---

## Sub-Plans

### 04-01: Show Device Configuration
**Goal:** Implement configuration viewing commands

**Commands:**
- `ensp-cli show-config <device>` - Display running configuration
- `ensp-cli show-interfaces <device>` - Display interface status
- `ensp-cli show-routes <device>` - Display routing table

**must_haves:**
- [ ] `show-config` displays running config with optional section filter
- [ ] `show-interfaces` shows interface status table
- [ ] `show-routes` displays routing table with protocol filter
- [ ] JSON output supported

### 04-02: Export Configuration
**Goal:** Implement configuration export to files

**Commands:**
- `ensp-cli export-config <device> -o <file>` - Export single device
- `ensp-cli export-all <directory>` - Export all devices

**Features:**
- Multiple formats: txt, json, markdown
- Metadata included (timestamp, topology, device info)
- Parallel fetching for export-all

**must_haves:**
- [ ] Single device export works
- [ ] Batch export works
- [ ] All formats generate valid output
- [ ] Metadata included

### 04-03: Compare Configurations
**Goal:** Implement configuration comparison

**Commands:**
- `ensp-cli diff-config <dev1> <dev2>` - Compare two devices
- `ensp-cli diff-file <device> <file>` - Compare with baseline
- `ensp-cli audit-configs` - Find inconsistencies across topology

**Features:**
- Section-specific comparison
- Smart ignore (timestamps, uptime)
- Similarity scoring
- Color-coded diff output

**must_haves:**
- [ ] Device-to-device comparison works
- [ ] Device-to-file comparison works
- [ ] Audit finds configuration drift
- [ ] Smart ignore filters volatile fields

### 04-04: Import Configuration
**Goal:** Implement configuration import from files to devices

**Commands:**
- `ensp-cli import-config <device> <file>` - Import to single device
- `ensp-cli import-all <directory>` - Import to multiple devices

**Features:**
- Dry-run mode for preview
- Dangerous command detection
- Section-specific import
- Template variable substitution
- Rollback on failure

**must_haves:**
- [ ] Configuration import from file works
- [ ] Dry-run mode previews changes
- [ ] Dangerous command warnings
- [ ] Batch import to multiple devices
- [ ] Template variables supported

---

## Execution Waves

| Wave | Plans | Description |
|------|-------|-------------|
| 1 | 04-01 | Config viewing (foundational) |
| 2 | 04-02, 04-04 | Config export and import (parallel, both depend on 04-01) |
| 3 | 04-03 | Config diff (depends on 04-01, 04-02) |

## Plan Files

- **04-01-show-config-PLAN.md** - Configuration viewing commands
- **04-02-export-config-PLAN.md** - Configuration export
- **04-03-diff-config-PLAN.md** - Configuration comparison
- **04-04-import-config-PLAN.md** - Configuration import

## Status

**Phase 4 Status:** 🔵 Planned (Redefined)  
**Dependencies:** Phase 1-3 (complete)  
**Ready for:** Execution

*Redefined: 2026-03-30*  
*Reason: Topology modification not feasible due to eNSP limitations*
