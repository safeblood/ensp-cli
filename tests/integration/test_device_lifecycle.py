"""Integration tests for device lifecycle management."""

import pytest
from pathlib import Path

from ensp_cli.models.running_device import RunningDevice
from ensp_cli.services.device_launcher import DeviceLauncher
from ensp_cli.services.process_manager import ProcessManager
from ensp_cli.services.topo_sync import TopoSyncService
from ensp_cli.services.mac_generator import MacGenerator
from ensp_cli.services.port_allocator import PortAllocator


class TestDeviceLifecycle:
    """Integration tests for full device lifecycle."""
    
    def test_register_and_unregister(self, tmp_path: Path) -> None:
        """Test device registration and unregistration."""
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
        
        # Register
        manager.register_device(device)
        assert manager.get_device("R1") is not None
        
        # Unregister
        removed = manager.unregister_device("R1")
        assert removed is not None
        assert manager.get_device("R1") is None
    
    def test_mac_generation_and_collision_avoidance(self) -> None:
        """Test MAC generation with collision avoidance."""
        mac_gen = MacGenerator()
        
        # Generate multiple MACs
        macs = set()
        for _ in range(50):
            mac = mac_gen.generate("router")
            assert mac not in macs, f"MAC collision: {mac}"
            macs.add(mac)
        
        assert len(macs) == 50
    
    def test_port_allocation_excludes_allocated(self) -> None:
        """Test that port allocator excludes already allocated ports."""
        alloc = PortAllocator(start=3000, end=3010)
        
        # Allocate several ports
        ports = [alloc.allocate() for _ in range(5)]
        
        # Verify all unique
        assert len(set(ports)) == 5
        
        # Release and reallocate
        released_port = ports[0]
        alloc.release(released_port)
        
        # Should be able to allocate the released port
        new_port = alloc.allocate()
        assert new_port == released_port
    
    def test_topology_backup_created(self, tmp_path: Path) -> None:
        """Test that topology backup is created on modification."""
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
        
        sync_service = TopoSyncService()
        sync_service.add_device_to_topo(topo_path, device)
        
        # Check backup created
        backups = list(tmp_path.glob("*.backup"))
        assert len(backups) == 1
    
    def test_device_coordinates_preserved(self, tmp_path: Path) -> None:
        """Test that device coordinates are preserved in topology."""
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
        
        sync_service = TopoSyncService()
        result = sync_service.add_device_to_topo(topo_path, device)
        
        # Device should have coordinates
        assert device.cx is not None
        assert device.cy is not None
        assert result["cx"] == device.cx
        assert result["cy"] == device.cy
    
    def test_custom_coordinates_override(self, tmp_path: Path) -> None:
        """Test that custom coordinates override auto-calculation."""
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
        
        sync_service = TopoSyncService()
        result = sync_service.add_device_to_topo(
            topo_path, device, custom_cx=999, custom_cy=888
        )
        
        assert result["cx"] == 999
        assert result["cy"] == 888
    
    def test_state_persists_across_instances(self, tmp_path: Path) -> None:
        """Test that state persists across ProcessManager instances."""
        state_file = tmp_path / "state.json"
        
        # First instance - add device
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
        
        # Second instance - should see device
        manager2 = ProcessManager(state_file=state_file)
        loaded = manager2.get_device("R1")
        
        assert loaded is not None
        assert loaded.name == "R1"
        assert loaded.model == "AR2220"
    
    def test_active_device_filtering(self, tmp_path: Path) -> None:
        """Test filtering of active devices."""
        state_file = tmp_path / "state.json"
        manager = ProcessManager(state_file=state_file)
        
        # Add running device
        running = RunningDevice(
            name="R1",
            device_type="router",
            model="AR2220",
            pid=12345,
            port=2000,
            mac_address="54-89-98-11-22-33",
            status="running",
        )
        manager.register_device(running)
        
        # Add stopped device
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
        
        # Get active only
        active = manager.list_devices(active_only=True)
        assert len(active) == 1
        assert active[0].name == "R1"
    
    def test_device_uptime_calculation(self) -> None:
        """Test device uptime calculation."""
        from datetime import datetime, timedelta
        
        device = RunningDevice(
            name="R1",
            device_type="router",
            model="AR2220",
            pid=12345,
            port=2000,
            mac_address="54-89-98-11-22-33",
            started_at=datetime.now() - timedelta(hours=1, minutes=30, seconds=45),
        )
        
        uptime_str = device.get_uptime_str()
        parts = uptime_str.split(":")
        assert len(parts) == 3
        
        # Should be 01:30:45
        assert parts[0] == "01"
        assert parts[1] == "30"
    
    def test_launcher_command_line_building(self) -> None:
        """Test that launcher builds correct command line."""
        launcher = DeviceLauncher()
        
        # Check that supported models are mapped
        assert "AR2220" in launcher.DEVICE_EXECUTABLES
        assert "AR3260" in launcher.DEVICE_EXECUTABLES
        assert "S5700" in launcher.DEVICE_EXECUTABLES
        assert "S3700" in launcher.DEVICE_EXECUTABLES
    
    def test_topology_device_removal(self, tmp_path: Path) -> None:
        """Test removing device from topology."""
        topo_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <topo>
            <devices>
                <dev id="1" name="R1" cx="100" cy="100"/>
                <dev id="2" name="R2" cx="200" cy="200"/>
            </devices>
        </topo>'''
        
        topo_path = tmp_path / "test.topo"
        topo_path.write_text(topo_content)
        
        sync_service = TopoSyncService()
        result = sync_service.remove_device_from_topo(topo_path, "R1")
        
        assert result["success"]
        
        # Verify only R2 remains
        root = sync_service.load_topology(topo_path)
        devices = root.find("devices")
        devs = devices.findall("dev")
        assert len(devs) == 1
        assert devs[0].get("name") == "R2"
    
    def test_remove_nonexistent_device(self, tmp_path: Path) -> None:
        """Test removing non-existent device from topology."""
        topo_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <topo>
            <devices>
                <dev id="1" name="R1" cx="100" cy="100"/>
            </devices>
        </topo>'''
        
        topo_path = tmp_path / "test.topo"
        topo_path.write_text(topo_content)
        
        sync_service = TopoSyncService()
        result = sync_service.remove_device_from_topo(topo_path, "NONEXISTENT")
        
        assert not result["success"]
        assert "not found" in result["message"]
