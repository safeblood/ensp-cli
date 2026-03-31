"""Tests for device launcher services."""

import pytest
from pathlib import Path
import xml.etree.ElementTree as ET

from ensp_cli.services.mac_generator import MacGenerator, generate_mac
from ensp_cli.services.port_allocator import PortAllocator, allocate_port
from ensp_cli.services.coordinate_allocator import CoordinateAllocator, allocate_coordinates
from ensp_cli.services.device_launcher import DeviceLauncher


class TestMacGenerator:
    """Test MAC address generator."""
    
    def test_generate_router_mac(self) -> None:
        """Test generating router MAC addresses."""
        gen = MacGenerator()
        mac = gen.generate("router")
        
        # Check format: XX-XX-XX-XX-XX-XX
        parts = mac.split("-")
        assert len(parts) == 6
        assert all(len(p) == 2 for p in parts)
        
        # Check Huawei OUI for routers
        assert mac.startswith("54-89-98")
    
    def test_generate_switch_mac(self) -> None:
        """Test generating switch MAC addresses."""
        gen = MacGenerator()
        mac = gen.generate("switch")
        
        # Check Huawei OUI for switches
        assert mac.startswith("4C-1F-CC")
    
    def test_mac_uniqueness(self) -> None:
        """Test that generated MACs are unique."""
        gen = MacGenerator()
        macs = {gen.generate("router") for _ in range(100)}
        assert len(macs) == 100
    
    def test_invalid_device_type(self) -> None:
        """Test error on invalid device type."""
        gen = MacGenerator()
        with pytest.raises(ValueError, match="Unsupported device type"):
            gen.generate("firewall")
    
    def test_release_mac(self) -> None:
        """Test releasing a MAC address."""
        gen = MacGenerator()
        mac = gen.generate("router")
        
        assert gen.is_used(mac)
        gen.release(mac)
        assert not gen.is_used(mac)
    
    def test_get_used_count(self) -> None:
        """Test getting count of used MACs."""
        gen = MacGenerator()
        assert gen.get_used_count() == 0
        
        gen.generate("router")
        assert gen.get_used_count() == 1
        
        gen.generate("switch")
        assert gen.get_used_count() == 2
    
    def test_clear(self) -> None:
        """Test clearing all MACs."""
        gen = MacGenerator()
        gen.generate("router")
        gen.generate("switch")
        
        assert gen.get_used_count() == 2
        gen.clear()
        assert gen.get_used_count() == 0
    
    def test_global_generate_mac(self) -> None:
        """Test global generate_mac function."""
        mac = generate_mac("router")
        assert mac.startswith("54-89-98")


class TestPortAllocator:
    """Test port allocator."""
    
    def test_allocate_port(self) -> None:
        """Test allocating a port."""
        alloc = PortAllocator(start=3000, end=3010)
        port = alloc.allocate()
        
        assert 3000 <= port <= 3010
        assert alloc.is_allocated(port)
    
    def test_allocate_specific_port(self) -> None:
        """Test allocating a specific port."""
        alloc = PortAllocator(start=3000, end=3010)
        port = alloc.allocate(preferred_port=3005)
        
        assert port == 3005
    
    def test_release_port(self) -> None:
        """Test releasing a port."""
        alloc = PortAllocator(start=3000, end=3010)
        port = alloc.allocate()
        
        assert alloc.is_allocated(port)
        alloc.release(port)
        assert not alloc.is_allocated(port)
    
    def test_get_allocated_ports(self) -> None:
        """Test getting all allocated ports."""
        alloc = PortAllocator(start=3000, end=3010)
        
        port1 = alloc.allocate()
        port2 = alloc.allocate()
        
        allocated = alloc.get_allocated_ports()
        assert port1 in allocated
        assert port2 in allocated
        assert len(allocated) == 2
    
    def test_port_range_exhausted(self) -> None:
        """Test error when port range exhausted."""
        alloc = PortAllocator(start=3000, end=3001)
        alloc.allocate()  # 3000
        alloc.allocate()  # 3001
        
        with pytest.raises(RuntimeError, match="No available ports"):
            alloc.allocate()
    
    def test_global_allocate_port(self) -> None:
        """Test global allocate_port function."""
        port = allocate_port()
        assert 2000 <= port <= 2100


class TestCoordinateAllocator:
    """Test coordinate allocator."""
    
    def test_default_allocation(self) -> None:
        """Test default coordinate allocation."""
        alloc = CoordinateAllocator()
        cx, cy = alloc.allocate()
        
        assert cx == 100
        assert cy == 100
    
    def test_custom_coordinates(self) -> None:
        """Test custom coordinate override."""
        alloc = CoordinateAllocator()
        cx, cy = alloc.allocate(custom_x=500, custom_y=300)
        
        assert cx == 500
        assert cy == 300
    
    def test_calculate_from_topology(self, tmp_path: Path) -> None:
        """Test coordinate calculation from topology file."""
        # Create test topology
        topo_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <topo>
            <dev id="1" name="R1" cx="100" cy="100"/>
            <dev id="2" name="R2" cx="200" cy="100"/>
        </topo>'''
        
        topo_path = tmp_path / "test.topo"
        topo_path.write_text(topo_content)
        
        alloc = CoordinateAllocator(grid_size=100)
        cx, cy = alloc.allocate(topo_path=topo_path)
        
        # Should be to the right of R2
        assert cx == 300
        assert cy == 100
    
    def test_empty_topology(self, tmp_path: Path) -> None:
        """Test allocation with empty topology."""
        topo_content = '<?xml version="1.0" encoding="UTF-8"?><topo></topo>'
        
        topo_path = tmp_path / "test.topo"
        topo_path.write_text(topo_content)
        
        alloc = CoordinateAllocator()
        cx, cy = alloc.allocate(topo_path=topo_path)
        
        assert cx == 100
        assert cy == 100
    
    def test_get_device_positions(self, tmp_path: Path) -> None:
        """Test getting device positions from topology."""
        topo_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <topo>
            <dev id="1" name="R1" cx="100" cy="100"/>
            <dev id="2" name="R2" cx="200" cy="200"/>
        </topo>'''
        
        topo_path = tmp_path / "test.topo"
        topo_path.write_text(topo_content)
        
        alloc = CoordinateAllocator()
        positions = alloc.get_device_positions(topo_path)
        
        assert len(positions) == 2
        assert (100, 100) in positions
        assert (200, 200) in positions
    
    def test_would_overlap(self, tmp_path: Path) -> None:
        """Test overlap detection."""
        topo_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <topo>
            <dev id="1" name="R1" cx="100" cy="100"/>
        </topo>'''
        
        topo_path = tmp_path / "test.topo"
        topo_path.write_text(topo_content)
        
        alloc = CoordinateAllocator()
        
        # Close position should overlap
        assert alloc.would_overlap(topo_path, 105, 105, threshold=50)
        
        # Far position should not overlap
        assert not alloc.would_overlap(topo_path, 500, 500, threshold=50)
    
    def test_global_allocate_coordinates(self) -> None:
        """Test global allocate_coordinates function."""
        cx, cy = allocate_coordinates()
        assert cx == 100
        assert cy == 100


class TestDeviceLauncher:
    """Test device launcher."""
    
    def test_launcher_creation(self) -> None:
        """Test launcher initialization."""
        launcher = DeviceLauncher()
        assert launcher is not None
    
    def test_invalid_router_model(self) -> None:
        """Test error on invalid router model."""
        launcher = DeviceLauncher()
        with pytest.raises(ValueError, match="Unsupported router model"):
            launcher.launch_router("R1", model="INVALID")
    
    def test_invalid_switch_model(self) -> None:
        """Test error on invalid switch model."""
        launcher = DeviceLauncher()
        with pytest.raises(ValueError, match="Unsupported switch model"):
            launcher.launch_switch("S1", model="INVALID")
    
    def test_supported_models(self) -> None:
        """Test that supported models are defined."""
        assert "AR2220" in DeviceLauncher.DEVICE_EXECUTABLES
        assert "AR3260" in DeviceLauncher.DEVICE_EXECUTABLES
        assert "S3700" in DeviceLauncher.DEVICE_EXECUTABLES
        assert "S5700" in DeviceLauncher.DEVICE_EXECUTABLES
