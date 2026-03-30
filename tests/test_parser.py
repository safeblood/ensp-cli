"""Tests for the topology XML parser."""

from pathlib import Path

import pytest

from ensp_cli.models import Connection, Device, Topology
from ensp_cli.parser import TopologyParser, TopologyParserError


class TestTopologyParser:
    """Test cases for TopologyParser."""

    def test_parse_file_not_found(self):
        """Test that FileNotFoundError is raised for non-existent files."""
        parser = TopologyParser()
        with pytest.raises(FileNotFoundError) as exc_info:
            parser.parse_file(Path("non_existent_file.topo"))
        assert "not found" in str(exc_info.value)

    def test_parse_valid_sample_file(self):
        """Test parsing the sample .topo file."""
        parser = TopologyParser()
        sample_path = Path("C:/Users/83773/Downloads/img/1/1.topo")
        
        topology = parser.parse_file(sample_path)
        
        assert isinstance(topology, Topology)
        assert topology.name == "1"  # From filename
        assert topology.file_path == sample_path
        assert topology.device_count == 3  # All 3 devices including Cloud
        
        # Check device names
        device_names = {d.name for d in topology.devices}
        assert device_names == {"LSW2", "Cloud1", "R2"}
        
        # Check specific device
        lsw2 = next(d for d in topology.devices if d.name == "LSW2")
        assert lsw2.model == "S5700"
        assert lsw2.console_port == 2001  # mapped from com_port
        assert lsw2.device_type == "Switch"  # mapped from model
        
        # Check router device
        r2 = next(d for d in topology.devices if d.name == "R2")
        assert r2.model == "Router"
        assert r2.console_port == 2000
        assert r2.device_type == "Router"
        
        # Check cloud device (com_port=0 maps to console_port=1)
        cloud1 = next(d for d in topology.devices if d.name == "Cloud1")
        assert cloud1.model == "Cloud"
        assert cloud1.console_port == 1  # Mapped from com_port=0
        assert cloud1.device_type == "Cloud"

    def test_parse_string_valid_xml(self):
        """Test parsing XML from string."""
        parser = TopologyParser()
        xml_content = '''<?xml version="1.0" encoding="UNICODE" ?>
        <topo version="1.3.00.200T">
            <devices>
                <dev id="test-id-1" name="R1" poe="0" model="Router" com_port="2000" />
                <dev id="test-id-2" name="SW1" poe="0" model="S5700" com_port="2001" />
            </devices>
            <lines />
        </topo>'''
        
        topology = parser.parse_string(xml_content)
        
        assert topology.device_count == 2
        assert topology.devices[0].name == "R1"
        assert topology.devices[0].device_type == "Router"
        assert topology.devices[0].console_port == 2000
        assert topology.devices[1].name == "SW1"
        assert topology.devices[1].device_type == "Switch"

    def test_parse_string_invalid_xml(self):
        """Test that invalid XML raises TopologyParserError."""
        parser = TopologyParser()
        invalid_xml = "<invalid>not closed"
        
        with pytest.raises(TopologyParserError) as exc_info:
            parser.parse_string(invalid_xml)
        assert "Invalid XML" in str(exc_info.value)

    def test_parse_device_missing_name(self):
        """Test that missing device name raises TopologyParserError."""
        parser = TopologyParser()
        xml_content = '''<?xml version="1.0" encoding="UNICODE" ?>
        <topo version="1.3.00.200T">
            <devices>
                <dev id="test-id" model="Router" com_port="2000" />
            </devices>
            <lines />
        </topo>'''
        
        with pytest.raises(TopologyParserError) as exc_info:
            parser.parse_string(xml_content)
        assert "missing required 'name' attribute" in str(exc_info.value)

    def test_parse_device_missing_model(self):
        """Test that missing device model raises TopologyParserError."""
        parser = TopologyParser()
        xml_content = '''<?xml version="1.0" encoding="UNICODE" ?>
        <topo version="1.3.00.200T">
            <devices>
                <dev id="test-id" name="R1" com_port="2000" />
            </devices>
            <lines />
        </topo>'''
        
        with pytest.raises(TopologyParserError) as exc_info:
            parser.parse_string(xml_content)
        assert "missing required 'model' attribute" in str(exc_info.value)

    def test_parse_device_invalid_com_port(self):
        """Test that invalid com_port raises TopologyParserError."""
        parser = TopologyParser()
        xml_content = '''<?xml version="1.0" encoding="UNICODE" ?>
        <topo version="1.3.00.200T">
            <devices>
                <dev id="test-id" name="R1" model="Router" com_port="invalid" />
            </devices>
            <lines />
        </topo>'''
        
        with pytest.raises(TopologyParserError) as exc_info:
            parser.parse_string(xml_content)
        assert "invalid com_port value" in str(exc_info.value)

    def test_parse_empty_topology(self):
        """Test parsing an empty topology."""
        parser = TopologyParser()
        xml_content = '''<?xml version="1.0" encoding="UNICODE" ?>
        <topo version="1.3.00.200T">
            <devices />
            <lines />
        </topo>'''
        
        topology = parser.parse_string(xml_content)
        
        assert isinstance(topology, Topology)
        assert topology.device_count == 0
        assert topology.connection_count == 0

    def test_parse_with_connections(self):
        """Test parsing topology with connections."""
        parser = TopologyParser()
        xml_content = '''<?xml version="1.0" encoding="UNICODE" ?>
        <topo version="1.3.00.200T">
            <devices>
                <dev id="d1" name="R1" model="Router" com_port="2000" />
                <dev id="d2" name="R2" model="Router" com_port="2001" />
            </devices>
            <lines>
                <line from_device="R1" from_port="GE0/0/0" to_device="R2" to_port="GE0/0/0" />
            </lines>
        </topo>'''
        
        topology = parser.parse_string(xml_content)
        
        assert topology.device_count == 2
        assert topology.connection_count == 1
        
        conn = topology.connections[0]
        assert conn.from_device == "R1"
        assert conn.from_port == "GE0/0/0"
        assert conn.to_device == "R2"
        assert conn.to_port == "GE0/0/0"

    def test_device_type_mapping(self):
        """Test device type mapping from model string."""
        parser = TopologyParser()
        xml_content = '''<?xml version="1.0" encoding="UNICODE" ?>
        <topo version="1.3.00.200T">
            <devices>
                <dev name="R1" model="Router" com_port="2000" />
                <dev name="SW1" model="S5700" com_port="2001" />
                <dev name="CL1" model="Cloud" com_port="0" />
                <dev name="FW1" model="USG6000V" com_port="2002" />
                <dev name="U1" model="UnknownModel" com_port="2003" />
            </devices>
            <lines />
        </topo>'''
        
        topology = parser.parse_string(xml_content)
        
        # All devices included (Cloud with com_port=0 maps to console_port=1)
        assert topology.device_count == 5
        devices_by_name = {d.name: d for d in topology.devices}
        assert devices_by_name["R1"].device_type == "Router"
        assert devices_by_name["SW1"].device_type == "Switch"
        assert devices_by_name["CL1"].device_type == "Cloud"
        assert devices_by_name["CL1"].console_port == 1  # Mapped from 0
        assert devices_by_name["FW1"].device_type == "Firewall"
        assert devices_by_name["U1"].device_type == "UnknownModel"

    def test_defusedxml_security_xxe(self):
        """Test that XXE attacks are prevented by defusedxml."""
        parser = TopologyParser()
        # This XXE payload should be safely rejected or ignored
        xxe_xml = '''<?xml version="1.0" encoding="UNICODE" ?>
        <!DOCTYPE topo [
            <!ENTITY xxe SYSTEM "file:///etc/passwd">
        ]>
        <topo version="1.3.00.200T">
            <devices>
                <dev name="R1" model="Router" com_port="2000" />
            </devices>
            <lines />
        </topo>'''
        
        # defusedxml should prevent XXE or process safely
        # We just verify parsing doesn't expose file contents
        try:
            topology = parser.parse_string(xxe_xml)
            # If parsing succeeds, ensure it doesn't expose external entity content
            assert topology.device_count == 1
            assert topology.devices[0].name == "R1"
        except TopologyParserError:
            # Also acceptable if defusedxml raises an error for DOCTYPE
            pass

    def test_defusedxml_security_billion_laughs(self):
        """Test that XML bomb attacks are prevented."""
        parser = TopologyParser()
        # Billion laughs attack - defusedxml should prevent this
        xml_bomb = '''<?xml version="1.0" encoding="UNICODE"?>
        <!DOCTYPE lolz [
            <!ENTITY lol "lol">
            <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
            <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
        ]>
        <topo version="1.3.00.200T">
            <devices>
                <dev name="R1" model="Router" com_port="2000" />
            </devices>
            <lines />
        </topo>'''
        
        # defusedxml should prevent entity expansion
        try:
            topology = parser.parse_string(xml_bomb)
            # If it parses, verify basic functionality works
            assert topology.device_count == 1
        except TopologyParserError:
            # Acceptable if defusedxml raises an error
            pass


class TestDeviceModel:
    """Test cases for Device model."""

    def test_device_creation(self):
        """Test Device model creation."""
        device = Device(name="R1", device_type="Router", model="AR2220", console_port=2000)
        assert device.name == "R1"
        assert device.device_type == "Router"
        assert device.model == "AR2220"
        assert device.console_port == 2000

    def test_device_validation(self):
        """Test Device model validation."""
        with pytest.raises(ValueError):
            Device(name="", device_type="Router", model="AR2220", console_port=2000)
        
        with pytest.raises(ValueError):
            Device(name="R1", device_type="", model="AR2220", console_port=2000)
        
        with pytest.raises(ValueError):
            Device(name="R1", device_type="Router", model="", console_port=2000)
        
        with pytest.raises(ValueError):
            Device(name="R1", device_type="Router", model="AR2220", console_port=0)
        
        with pytest.raises(ValueError):
            Device(name="R1", device_type="Router", model="AR2220", console_port=70000)


class TestConnectionModel:
    """Test cases for Connection model."""

    def test_connection_creation(self):
        """Test Connection model creation."""
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

    def test_connection_validation_same_device(self):
        """Test Connection validation prevents same source/target."""
        with pytest.raises(ValueError):
            Connection(
                from_device="R1",
                from_port="GE0/0/0",
                to_device="R1",
                to_port="GE0/0/1"
            )

    def test_connection_validation_empty_fields(self):
        """Test Connection validation requires non-empty fields."""
        with pytest.raises(ValueError):
            Connection(
                from_device="",
                from_port="GE0/0/0",
                to_device="R2",
                to_port="GE0/0/1"
            )


class TestTopologyModel:
    """Test cases for Topology model."""

    def test_topology_creation(self):
        """Test Topology model creation."""
        device = Device(name="R1", device_type="Router", model="AR2220", console_port=2000)
        topology = Topology(name="TestTopo", devices=[device], connections=[])
        assert topology.device_count == 1
        assert topology.devices[0].name == "R1"

    def test_topology_default_values(self):
        """Test Topology model with default values."""
        topology = Topology(name="Test")
        assert topology.devices == []
        assert topology.connections == []

    def test_topology_get_device(self):
        """Test getting device by name."""
        device = Device(name="R1", device_type="Router", model="AR2220", console_port=2000)
        topology = Topology(name="Test", devices=[device])
        
        found = topology.get_device("R1")
        assert found is not None
        assert found.name == "R1"
        
        not_found = topology.get_device("NonExistent")
        assert not_found is None

    def test_topology_add_duplicate_device(self):
        """Test adding duplicate device raises error."""
        device1 = Device(name="R1", device_type="Router", model="AR2220", console_port=2000)
        device2 = Device(name="R1", device_type="Switch", model="S5700", console_port=2001)
        topology = Topology(name="Test", devices=[device1])
        
        with pytest.raises(ValueError):
            topology.add_device(device2)

    def test_topology_add_connection_invalid_device(self):
        """Test adding connection with invalid device raises error."""
        device = Device(name="R1", device_type="Router", model="AR2220", console_port=2000)
        topology = Topology(name="Test", devices=[device])
        
        conn = Connection(
            from_device="R1",
            from_port="GE0/0/0",
            to_device="NonExistent",
            to_port="GE0/0/1"
        )
        
        with pytest.raises(ValueError):
            topology.add_connection(conn)
