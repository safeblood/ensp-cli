"""Topology synchronization service for CLI-GUI integration."""

import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional

from ensp_cli.models.running_device import RunningDevice
from ensp_cli.services.coordinate_allocator import CoordinateAllocator


class TopoSyncService:
    """Synchronize device state with topology file.
    
    Updates .topo file to include CLI-launched devices so they
    appear correctly in the eNSP GUI.
    """
    
    def __init__(self, coordinate_allocator: Optional[CoordinateAllocator] = None) -> None:
        """Initialize the topology sync service.
        
        Args:
            coordinate_allocator: Coordinate allocator (creates default if None)
        """
        self._coord_alloc = coordinate_allocator or CoordinateAllocator()
    
    def load_topology(self, topo_path: Path) -> ET.Element:
        """Load and parse topology file.
        
        Args:
            topo_path: Path to topology file
            
        Returns:
            Root XML element
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ET.ParseError: If XML is invalid
        """
        if not topo_path.exists():
            raise FileNotFoundError(f"Topology file not found: {topo_path}")
        
        # Handle eNSP's "UNICODE" encoding (actually UTF-8 but declared as UNICODE)
        content = topo_path.read_text(encoding='utf-8', errors='ignore')
        
        # Replace UNICODE encoding declaration with UTF-8
        content = content.replace('encoding="UNICODE"', 'encoding="UTF-8"')
        
        # Parse from string
        root = ET.fromstring(content)
        
        return root
    
    def add_device_to_topo(
        self,
        topo_path: Path,
        device: RunningDevice,
        custom_cx: Optional[int] = None,
        custom_cy: Optional[int] = None
    ) -> dict:
        """Add a device to the topology file.
        
        Args:
            topo_path: Path to topology file
            device: Device to add
            custom_cx: Optional custom X coordinate
            custom_cy: Optional custom Y coordinate
            
        Returns:
            Dictionary with result info
        """
        # Backup original file
        self._backup_topo(topo_path)
        
        # Load topology
        tree = ET.parse(topo_path)
        root = tree.getroot()
        
        # Find or create devices element
        devices_elem = root.find("devices")
        if devices_elem is None:
            devices_elem = ET.SubElement(root, "devices")
        
        # Calculate next device ID
        next_id = self._get_next_device_id(devices_elem)
        
        # Calculate coordinates
        cx, cy = self._coord_alloc.allocate(
            topo_path=topo_path,
            custom_x=custom_cx,
            custom_y=custom_cy
        )
        
        # Create device element
        dev_elem = ET.SubElement(devices_elem, "dev")
        dev_elem.set("id", str(next_id))
        dev_elem.set("name", device.name)
        dev_elem.set("model", self._map_model(device.model))
        dev_elem.set("device_type", device.device_type)
        dev_elem.set("cx", str(cx))
        dev_elem.set("cy", str(cy))
        dev_elem.set("com_port", str(device.port))
        dev_elem.set("source", "cli")
        
        # Save updated topology
        tree.write(topo_path, encoding="UTF-8", xml_declaration=True)
        
        # Update device with coordinates
        device.cx = cx
        device.cy = cy
        
        return {
            "success": True,
            "device_id": next_id,
            "cx": cx,
            "cy": cy,
            "backup_created": True,
        }
    
    def remove_device_from_topo(self, topo_path: Path, device_name: str) -> dict:
        """Remove a device from the topology file.
        
        Args:
            topo_path: Path to topology file
            device_name: Name of device to remove
            
        Returns:
            Dictionary with result info
        """
        # Backup original file
        self._backup_topo(topo_path)
        
        # Load topology
        tree = ET.parse(topo_path)
        root = tree.getroot()
        
        # Find devices element
        devices_elem = root.find("devices")
        if devices_elem is None:
            return {
                "success": False,
                "message": "No devices element found",
            }
        
        # Find and remove device
        removed = False
        for dev in devices_elem.findall("dev"):
            if dev.get("name") == device_name:
                devices_elem.remove(dev)
                removed = True
                break
        
        if removed:
            tree.write(topo_path, encoding="UTF-8", xml_declaration=True)
            return {
                "success": True,
                "message": f"Device '{device_name}' removed from topology",
            }
        
        return {
            "success": False,
            "message": f"Device '{device_name}' not found in topology",
        }
    
    def get_gui_devices(self) -> list[dict]:
        """Scan for GUI-launched eNSP devices.
        
        Returns:
            List of GUI device info dictionaries
        """
        devices = []
        
        try:
            # Get eNSP process PIDs
            router_pids = self._get_pids("eNSP_Router.exe")
            switch_pids = self._get_pids("eNSP_Switch.exe")
            
            # Get port mappings
            port_map = self._get_port_mappings()
            
            # Build device info
            for pid in router_pids:
                devices.append({
                    "pid": pid,
                    "device_type": "router",
                    "ports": port_map.get(pid, []),
                    "source": "gui",
                })
            
            for pid in switch_pids:
                devices.append({
                    "pid": pid,
                    "device_type": "switch",
                    "ports": port_map.get(pid, []),
                    "source": "gui",
                })
                
        except Exception:
            pass
        
        return devices
    
    def sync_running_state(
        self,
        topo_path: Path,
        cli_devices: list[RunningDevice]
    ) -> dict:
        """Synchronize running state with topology.
        
        Args:
            topo_path: Path to topology file
            cli_devices: List of CLI-launched devices
            
        Returns:
            Dictionary with sync results
        """
        gui_devices = self.get_gui_devices()
        
        # Load topology
        try:
            tree = ET.parse(topo_path)
            root = tree.getroot()
        except (FileNotFoundError, ET.ParseError):
            return {
                "success": False,
                "message": "Failed to load topology",
            }
        
        results = {
            "gui_devices_found": len(gui_devices),
            "cli_devices_synced": 0,
            "orphaned_removed": 0,
        }
        
        # Find devices element
        devices_elem = root.find("devices")
        if devices_elem is None:
            devices_elem = ET.SubElement(root, "devices")
        
        # Get existing device names
        existing_names = {
            dev.get("name") for dev in devices_elem.findall("dev")
        }
        
        # Sync CLI devices
        for device in cli_devices:
            if device.name not in existing_names:
                # Add missing CLI device
                self.add_device_to_topo(topo_path, device)
                results["cli_devices_synced"] += 1
        
        # Save changes
        tree.write(topo_path, encoding="UTF-8", xml_declaration=True)
        
        return results
    
    def _backup_topo(self, topo_path: Path) -> Path:
        """Create backup of topology file.
        
        Args:
            topo_path: Path to topology file
            
        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = topo_path.parent / f"{topo_path.stem}_{timestamp}.topo.backup"
        
        shutil.copy2(topo_path, backup_path)
        return backup_path
    
    def _get_next_device_id(self, devices_elem: ET.Element) -> int:
        """Get next available device ID.
        
        Args:
            devices_elem: Devices XML element
            
        Returns:
            Next device ID
        """
        max_id = 0
        for dev in devices_elem.findall("dev"):
            try:
                dev_id = int(dev.get("id", 0))
                max_id = max(max_id, dev_id)
            except ValueError:
                continue
        
        return max_id + 1
    
    def _map_model(self, model: str) -> str:
        """Map device model to topology model name.
        
        Args:
            model: Device model (AR2220, S5700, etc.)
            
        Returns:
            Topology model name
        """
        model_map = {
            "AR2220": "AR2220_Router",
            "AR3260": "AR3260_Router",
            "S3700": "S3700_Switch",
            "S5700": "S5700_Switch",
        }
        return model_map.get(model, f"{model}_Device")
    
    def _get_pids(self, process_name: str) -> list[int]:
        """Get PIDs for a process name.
        
        Args:
            process_name: Name of process
            
        Returns:
            List of PIDs
        """
        pids = []
        
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/FO", "CSV"],
                capture_output=True,
                text=True,
                encoding="gbk",
                errors="ignore"
            )
            
            lines = result.stdout.strip().splitlines()
            for line in lines[1:]:  # Skip header
                parts = line.split('","')
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1].replace('"', ''))
                        pids.append(pid)
                    except ValueError:
                        continue
        except Exception:
            pass
        
        return pids
    
    def _get_port_mappings(self) -> dict[int, list[int]]:
        """Get port to PID mappings.
        
        Returns:
            Dictionary mapping PID to list of ports
        """
        port_map: dict[int, list[int]] = {}
        
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                encoding="gbk",
                errors="ignore"
            )
            
            for line in result.stdout.splitlines():
                if "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        local_addr = parts[1]
                        if ":" in local_addr:
                            try:
                                port = int(local_addr.split(":")[-1])
                                pid = int(parts[-1])
                                
                                if pid not in port_map:
                                    port_map[pid] = []
                                port_map[pid].append(port)
                            except ValueError:
                                continue
        except Exception:
            pass
        
        return port_map


# Global instance for convenience
_default_service: TopoSyncService | None = None


def get_service() -> TopoSyncService:
    """Get the default topology sync service instance."""
    global _default_service
    if _default_service is None:
        _default_service = TopoSyncService()
    return _default_service
