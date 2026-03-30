# Phase 4: Device Operations - Context

**Gathered:** 2026-03-30

## Decisions

### Device Type Support
- **Supported device types:** Router, Switch, Firewall, Cloud
- **Validation:** Hardcoded list - reject unsupported types with helpful error message
- **Model mapping:** Each type has default model (e.g., Router -> AR2220, Switch -> S3700)

### Port/Interface Specification
- **Interface naming:** Support both formats:
  - `GE0/0/1` (GigabitEthernet)
  - `Ethernet0/0/1` (Ethernet)
- **Auto-suggest:** CLI should suggest available ports when user types `--port1` or `--port2`
- **Validation:** Verify port exists on device and is not already connected

### Save Behavior
- **Primary:** Auto-save after each modification command
- **Override:** `--no-save` flag to skip persistence (for dry-run/testing)
- **Backup:** Create `.topo.bak` before each save operation

### Coordinate & Port Assignment
- **X/Y Coordinates:**
  - Auto-assign to avoid overlap with existing devices
  - Use grid-based placement algorithm
  - Default spacing: 100 units between devices
- **Console Port:**
  - Auto-assign unique port (incremental from highest existing)
  - Range: 2000-65535
  - Skip ports already in use

### Validation Strictness
- **Device Names:**
  - Prevent duplicate names (case-insensitive)
  - Validate format: alphanumeric + hyphen/underscore only
  - Max length: 32 characters
- **Interface Compatibility:**
  - Validate interface type matches device capabilities
  - Router: GE, Ethernet, Serial
  - Switch: GE, Ethernet
  - Firewall: GE, Ethernet
  - Cloud: Ethernet only (virtual)

## Claude's Discretion

- Specific error message wording
- Grid placement algorithm details (spiral vs linear)
- Backup file naming convention (timestamp vs simple .bak)
- Auto-suggest UI implementation (completions vs list display)

## Deferred Ideas

- Allow custom device models beyond defaults
- Support VLAN configuration during connect
- Batch operations (add multiple devices at once)
- Undo/redo functionality

---
*Context gathered for phase planning*
