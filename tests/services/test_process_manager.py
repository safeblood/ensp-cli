"""Tests for process manager services."""

import json
import pytest
from datetime import datetime
from pathlib import Path

from ensp_cli.models.running_device import RunningDevice
from ensp_cli.services.process_manager import ProcessManager
from ensp_cli.services.topo_sync import TopoSyncService


class TestRunningDevice:
    """Test RunningDevice model."""
    
    def test_create_device(self) -> None:
        """Test creating a running device."""
        device = RunningDevice(
            name="R1",
            device_type="router",
            model="AR2220",
            pid=12345,
            port=2000,
            mac_address="54-89-98-11-22-33",
        )
        
        assert device.name == "R1"
        assert device.device_type == "router"
        assert device.status == "starting"
        assert device.source == "cli"
    
    def test_invalid_device_type(self) -> None:
        """Test error on invalid device type."""
        with pytest.raises(ValueError, match="device_type must be one of"):
            RunningDevice(
                name="R1",
                device_type="invalid",
                model="AR2220",
                pid=12345,
                port=2000,
                mac_address="54-89-98-11-22-33",
            )
    
    def test_invalid_status(self) -> None:
        """Test error on invalid status."""
        with pytest.raises(ValueError, match="status must be one of"):
            RunningDevice(
                name="R1",
                device_type="router",
                model="AR2220",
                pid=12345,
                port=2000,
                mac_address="54-89-98-11-22-33",
                status="invalid",
            )
    
    def test_status_transitions(self) -> None:
        """Test status transition methods."""
        device = RunningDevice(
            name="R1",
            device_type="router",
            model="AR2220",
            pid=12345,
            port=2000,
            mac_address="54-89-98-11-22-33",
        )
        
        assert device.status == "starting"
        assert device.is_active()
        
        device.to_running()
        assert device.status == "running"
        assert device.is_active()
        
        device.to_stopped()
        assert device.status == "stopped"
        assert not device.is_active()
    
    def test_error_transition(self) -> None:
        """Test error status transition."""
        device = RunningDevice(
            name="R1",
            device_type="router",
            model="AR2220",
            pid=12345,
            port=2000,
            mac_address="54-89-98-11-22-33",
        )
        
        device.to_error("Connection failed")
        assert device.status == "error"
        assert not device.is_active()
    
    def test_uptime(self) -> None:
        """Test uptime calculation."""
        device = RunningDevice(
            name="R1",
            device_type="router",
            model="AR2220",
            pid=12345,
            port=2000,
            mac_address="54-89-98-11-22-33",
            started_at=datetime.now(),
        )
        
        uptime = device.get_uptime_seconds()
        assert uptime >= 0
        
        uptime_str = device.get_uptime_str()
        assert ":" in uptime_str
        parts = uptime_str.split(":")
        assert len(parts) == 3


class TestProcessManager:
    """Test ProcessManager."""
    
    def test_register_device(self, tmp_path: Path) -> None:
        """Test registering a device."""
        state_file = tmp_path / "state.json"
        manager = ProcessManager(state_file=state_file)
        
        device = RunningDevice(
            name="R1",
            device_type="router",
            model="AR2220",
            pid=12345,
            port=2000,
            mac_address="54-89-98-11-22-33",
        )
        
        manager.register_device(device)
        
        assert manager.get_device("R1") is not None
        assert manager.get_device("R1").name == "R1"
    
    def test_unregister_device(self, tmp_path: Path) -> None:
        """Test unregistering a device."""
        state_file = tmp_path / "state.json"
        manager = ProcessManager(state_file=state_file)
        
        device = RunningDevice(
            name="R1",
            device_type="router",
            model="AR2220",
            pid=12345,
            port=2000,
            mac_address="54-89-98-11-22-33",
        )
        
        manager.register_device(device)
        removed = manager.unregister_device("R1")
        
        assert removed is not None
        assert removed.name == "R1"
        assert manager.get_device("R1") is None
    
    def test_list_devices(self, tmp_path: Path) -> None:
        """Test listing devices."""
        state_file = tmp_path / "state.json"
        manager = ProcessManager(state_file=state_file)
        
        # Register multiple devices
        for i in range(3):
            device = RunningDevice(
                name=f"R{i}",
                device_type="router",
                model="AR2220",
                pid=10000 + i,
                port=2000 + i,
                mac_address=f"54-89-98-11-22-{i:02d}",
            )
            manager.register_device(device)
        
        devices = manager.list_devices()
        assert len(devices) == 3
    
    def test_active_only_filter(self, tmp_path: Path) -> None:
        """Test active only filter."""
        state_file = tmp_path / "state.json"
        manager = ProcessManager(state_file=state_file)
        
        # Active device
        active = RunningDevice(
            name="R1",
            device_type="router",
            model="AR2220",
            pid=12345,
            port=2000,
            mac_address="54-89-98-11-22-33",
            status="running",
        )
        manager.register_device(active)
        
        # Stopped device
        stopped = RunningDevice(
            name="R2",
            device_type="router",
            model="AR2220",
            pid=12346,
            port=2001,
            mac_address="54-89-98-11-22-34",
            status="stopped",
        )
        manager.register_device(stopped)
        
        all_devices = manager.list_devices(active_only=False)
        assert len(all_devices) == 2
        
        active_devices = manager.list_devices(active_only=True)
        assert len(active_devices) == 1
        assert active_devices[0].name == "R1"
    
    def test_state_persistence(self, tmp_path: Path) -> None:
        """Test state save/load."""
        state_file = tmp_path / "state.json"
        
        # Create and save state
        manager1 = ProcessManager(state_file=state_file)
        device = RunningDevice(
            name="R1",
            device_type="router",
            model="AR2220",
            pid=12345,
            port=2000,
            mac_address="54-89-98-11-22-33",
        )
        manager1.register_device(device)
        
        # Load state in new manager
        manager2 = ProcessManager(state_file=state_file)
        loaded = manager2.get_device("R1")
        
        assert loaded is not None
        assert loaded.name == "R1"
        assert loaded.port == 2000
    
    def test_stop_nonexistent_device(self, tmp_path: Path) -> None:
        """Test stopping a non-existent device."""
        state_file = tmp_path / "state.json"
        manager = ProcessManager(state_file=state_file)
        
        result = manager.stop_device("NONEXISTENT")
        
        assert not result["success"]
        assert "not found" in result["message"]


class TestTopoSyncService:
    """Test TopoSyncService."""
    
    def test_load_topology(self, tmp_path: Path) -> None:
        """Test loading topology file."""
        topo_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <topo>
            <devices>
                <dev id="1" name="R1" cx="100" cy="100"/>
            </devices>
        </topo>'''
        
        topo_path = tmp_path / "test.topo"
        topo_path.write_text(topo_content)
        
        service = TopoSyncService()
        root = service.load_topology(topo_path)
        
        assert root.tag == "topo"
    
    def test_add_device_to_topo(self, tmp_path: Path) -> None:
        """Test adding device to topology."""
        topo_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <topo>
            <devices>
                <dev id="1" name="R1" cx="100" cy="100"/>
            </devices>
        </topo>'''
        
        topo_path = tmp_path / "test.topo"
        topo_path.write_text(topo_content)
        
        device = RunningDevice(
            name="R2",
            device_type="router",
            model="AR2220",
            pid=12345,
            port=2000,
            mac_address="54-89-98-11-22-33",
        )
        
        service = TopoSyncService()
        result = service.add_device_to_topo(topo_path, device)
        
        assert result["success"]
        assert result["device_id"] == 2
        assert result["cx"] > 100  # Should be to the right
        
        # Verify backup was created
        backup_files = list(tmp_path.glob("*.backup"))
        assert len(backup_files) == 1
    
    def test_remove_device_from_topo(self, tmp_path: Path) -> None:
        """Test removing device from topology."""
        topo_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <topo>
            <devices>
                <dev id="1" name="R1" cx="100" cy="100"/>
                <dev id="2" name="R2" cx="200" cy="100"/>
            </devices>
        </topo>'''
        
        topo_path = tmp_path / "test.topo"
        topo_path.write_text(topo_content)
        
        service = TopoSyncService()
        result = service.remove_device_from_topo(topo_path, "R1")
        
        assert result["success"]
        assert "removed" in result["message"]
        
        # Verify device removed
        root = service.load_topology(topo_path)
        devices = root.find("devices")
        assert len(devices.findall("dev")) == 1
    
    def test_custom_coordinates(self, tmp_path: Path) -> None:
        """Test adding device with custom coordinates."""
        topo_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <topo>
            <devices>
                <dev id="1" name="R1" cx="100" cy="100"/>
            </devices>
        </topo>'''
        
        topo_path = tmp_path / "test.topo"
        topo_path.write_text(topo_content)
        
        device = RunningDevice(
            name="R2",
            device_type="router",
            model="AR2220",
            pid=12345,
            port=2000,
            mac_address="54-89-98-11-22-33",
        )
        
        service = TopoSyncService()
        result = service.add_device_to_topo(
            topo_path, device, custom_cx=500, custom_cy=300
        )
        
        assert result["success"]
        assert result["cx"] == 500
        assert result["cy"] == 300
