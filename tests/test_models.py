"""Tests for eNSP CLI models."""

import pytest
from pydantic import ValidationError

from ensp_cli.models import Connection, Device, Topology


class TestDevice:
    """Tests for the Device model."""
    
    def test_device_creation(self):
        """Test creating a valid Device."""
        device = Device(
            name="R1",
            device_type="Router",
            model="AR2220",
            console_port=2000
        )
        assert device.name == "R1"
        assert device.device_type == "Router"
        assert device.model == "AR2220"
        assert device.console_port == 2000
    
    def test_device_str(self):
        """Test Device string representation."""
        device = Device(name="R1", device_type="Router", model="AR2220", console_port=2000)
        assert str(device) == "R1 (Router/AR2220, console=2000)"
    
    def test_device_empty_name_raises(self):
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError):
            Device(name="", device_type="Router", model="AR2220", console_port=2000)
    
    def test_device_whitespace_name_raises(self):
        """Test that whitespace-only name raises ValidationError."""
        with pytest.raises(ValidationError):
            Device(name="   ", device_type="Router", model="AR2220", console_port=2000)
    
    def test_device_empty_type_raises(self):
        """Test that empty device_type raises ValidationError."""
        with pytest.raises(ValidationError):
            Device(name="R1", device_type="", model="AR2220", console_port=2000)
    
    def test_device_empty_model_raises(self):
        """Test that empty model raises ValidationError."""
        with pytest.raises(ValidationError):
            Device(name="R1", device_type="Router", model="", console_port=2000)
    
    def test_device_invalid_console_port_zero(self):
        """Test that console_port 0 raises ValidationError."""
        with pytest.raises(ValidationError):
            Device(name="R1", device_type="Router", model="AR2220", console_port=0)
    
    def test_device_invalid_console_port_negative(self):
        """Test that negative console_port raises ValidationError."""
        with pytest.raises(ValidationError):
            Device(name="R1", device_type="Router", model="AR2220", console_port=-1)
    
    def test_device_invalid_console_port_too_high(self):
        """Test that console_port > 65535 raises ValidationError."""
        with pytest.raises(ValidationError):
            Device(name="R1", device_type="Router", model="AR2220", console_port=70000)
    
    def test_device_valid_boundary_ports(self):
        """Test valid boundary port numbers."""
        device1 = Device(name="R1", device_type="Router", model="AR2220", console_port=1)
        assert device1.console_port == 1
        
        device2 = Device(name="R2", device_type="Router", model="AR2220", console_port=65535)
        assert device2.console_port == 65535


class TestConnection:
    """Tests for the Connection model."""
    
    def test_connection_creation(self):
        """Test creating a valid Connection."""
        conn = Connection(
            from_device="R1",
            from_port="GE0/0/0",
            to_device="R2",
            to_port="GE0/0/1"
        )
        assert conn.from_device == "R1"
        assert conn.from_port == "GE0/0/0"
        assert conn.to_device == "R2"
        assert conn.to_port == "GE0/0/1"
    
    def test_connection_str(self):
        """Test Connection string representation."""
        conn = Connection(from_device="R1", from_port="GE0/0/0", to_device="R2", to_port="GE0/0/1")
        assert str(conn) == "R1:GE0/0/0 -> R2:GE0/0/1"
    
    def test_connection_same_device_raises(self):
        """Test that connection from device to itself raises ValidationError."""
        with pytest.raises(ValidationError):
            Connection(
                from_device="R1",
                from_port="GE0/0/0",
                to_device="R1",
                to_port="GE0/0/1"
            )
    
    def test_connection_empty_from_port_raises(self):
        """Test that empty from_port raises ValidationError."""
        with pytest.raises(ValidationError):
            Connection(from_device="R1", from_port="", to_device="R2", to_port="GE0/0/1")
    
    def test_connection_empty_to_port_raises(self):
        """Test that empty to_port raises ValidationError."""
        with pytest.raises(ValidationError):
            Connection(from_device="R1", from_port="GE0/0/0", to_device="R2", to_port="")
    
    def test_connection_involves_device(self):
        """Test the involves_device method."""
        conn = Connection(from_device="R1", from_port="GE0/0/0", to_device="R2", to_port="GE0/0/1")
        assert conn.involves_device("R1") is True
        assert conn.involves_device("R2") is True
        assert conn.involves_device("R3") is False


class TestTopology:
    """Tests for the Topology model."""
    
    def test_topology_creation(self):
        """Test creating a valid Topology."""
        device = Device(name="R1", device_type="Router", model="AR2220", console_port=2000)
        topology = Topology(name="test-topo", devices=[device])
        assert topology.name == "test-topo"
        assert len(topology.devices) == 1
        assert topology.device_count == 1
    
    def test_topology_empty_name_raises(self):
        """Test that empty topology name raises ValidationError."""
        with pytest.raises(ValidationError):
            Topology(name="")
    
    def test_topology_get_device_found(self):
        """Test get_device returns the device when found."""
        r1 = Device(name="R1", device_type="Router", model="AR2220", console_port=2000)
        r2 = Device(name="R2", device_type="Router", model="AR2220", console_port=2001)
        topology = Topology(name="test", devices=[r1, r2])
        
        found = topology.get_device("R1")
        assert found is not None
        assert found.name == "R1"
    
    def test_topology_get_device_not_found(self):
        """Test get_device returns None when device not found."""
        r1 = Device(name="R1", device_type="Router", model="AR2220", console_port=2000)
        topology = Topology(name="test", devices=[r1])
        
        found = topology.get_device("R99")
        assert found is None
    
    def test_topology_get_connections_for(self):
        """Test get_connections_for filters correctly."""
        r1 = Device(name="R1", device_type="Router", model="AR2220", console_port=2000)
        r2 = Device(name="R2", device_type="Router", model="AR2220", console_port=2001)
        s1 = Device(name="S1", device_type="Switch", model="S5700", console_port=2002)
        
        conn1 = Connection(from_device="R1", from_port="GE0/0/0", to_device="R2", to_port="GE0/0/0")
        conn2 = Connection(from_device="R1", from_port="GE0/0/1", to_device="S1", to_port="GE0/0/1")
        conn3 = Connection(from_device="R2", from_port="GE0/0/1", to_device="S1", to_port="GE0/0/2")
        
        topology = Topology(
            name="test",
            devices=[r1, r2, s1],
            connections=[conn1, conn2, conn3]
        )
        
        r1_conns = topology.get_connections_for("R1")
        assert len(r1_conns) == 2
        
        r2_conns = topology.get_connections_for("R2")
        assert len(r2_conns) == 2
        
        s1_conns = topology.get_connections_for("S1")
        assert len(s1_conns) == 2
        
        r99_conns = topology.get_connections_for("R99")
        assert len(r99_conns) == 0
    
    def test_topology_add_device(self):
        """Test add_device adds a device."""
        topology = Topology(name="test")
        device = Device(name="R1", device_type="Router", model="AR2220", console_port=2000)
        
        topology.add_device(device)
        assert topology.device_count == 1
        assert topology.get_device("R1") == device
    
    def test_topology_add_device_duplicate_raises(self):
        """Test add_device raises when device name already exists."""
        r1 = Device(name="R1", device_type="Router", model="AR2220", console_port=2000)
        topology = Topology(name="test", devices=[r1])
        
        r1_dup = Device(name="R1", device_type="Switch", model="S5700", console_port=2001)
        with pytest.raises(ValueError, match="already exists"):
            topology.add_device(r1_dup)
    
    def test_topology_add_connection(self):
        """Test add_connection adds a connection."""
        r1 = Device(name="R1", device_type="Router", model="AR2220", console_port=2000)
        r2 = Device(name="R2", device_type="Router", model="AR2220", console_port=2001)
        topology = Topology(name="test", devices=[r1, r2])
        
        conn = Connection(from_device="R1", from_port="GE0/0/0", to_device="R2", to_port="GE0/0/0")
        topology.add_connection(conn)
        
        assert topology.connection_count == 1
    
    def test_topology_add_connection_missing_source_raises(self):
        """Test add_connection raises when source device doesn't exist."""
        r2 = Device(name="R2", device_type="Router", model="AR2220", console_port=2001)
        topology = Topology(name="test", devices=[r2])
        
        conn = Connection(from_device="R1", from_port="GE0/0/0", to_device="R2", to_port="GE0/0/0")
        with pytest.raises(ValueError, match="Source device"):
            topology.add_connection(conn)
    
    def test_topology_add_connection_missing_target_raises(self):
        """Test add_connection raises when target device doesn't exist."""
        r1 = Device(name="R1", device_type="Router", model="AR2220", console_port=2000)
        topology = Topology(name="test", devices=[r1])
        
        conn = Connection(from_device="R1", from_port="GE0/0/0", to_device="R2", to_port="GE0/0/0")
        with pytest.raises(ValueError, match="Target device"):
            topology.add_connection(conn)
    
    def test_topology_device_count_property(self):
        """Test device_count property."""
        topology = Topology(name="test")
        assert topology.device_count == 0
        
        topology.devices.append(Device(name="R1", device_type="Router", model="AR2220", console_port=2000))
        assert topology.device_count == 1
    
    def test_topology_connection_count_property(self):
        """Test connection_count property."""
        topology = Topology(name="test")
        assert topology.connection_count == 0
        
        topology.connections.append(
            Connection(from_device="R1", from_port="GE0/0/0", to_device="R2", to_port="GE0/0/0")
        )
        assert topology.connection_count == 1
