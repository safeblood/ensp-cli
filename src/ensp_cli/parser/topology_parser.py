"""Secure XML parser for eNSP topology files."""

from pathlib import Path

import defusedxml.ElementTree as ET
from defusedxml.ElementTree import ParseError

from ensp_cli.models import Connection, Device, Topology


class TopologyParserError(Exception):
    """Base exception for topology parser errors."""
    pass


class TopologyParser:
    """Parser for eNSP .topo topology files using secure XML parsing.
    
    Uses defusedxml to prevent XXE attacks and XML bomb vulnerabilities.
    """

    def parse_file(self, path: Path) -> Topology:
        """Parse a .topo file and return a Topology model.
        
        Args:
            path: Path to the .topo file
            
        Returns:
            Topology model with devices and connections
            
        Raises:
            FileNotFoundError: If the file does not exist
            TopologyParserError: If XML parsing fails or required elements are missing
        """
        file_path = Path(path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Topology file not found: {file_path}")
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except ParseError as e:
            raise TopologyParserError(f"Invalid XML in topology file: {e}") from e
        except Exception as e:
            raise TopologyParserError(f"Failed to parse topology file: {e}") from e
        
        return self._parse_root(root)

    def parse_string(self, xml_content: str) -> Topology:
        """Parse XML content from a string.
        
        Args:
            xml_content: XML string to parse
            
        Returns:
            Topology model with devices and connections
            
        Raises:
            TopologyParserError: If XML parsing fails or required elements are missing
        """
        try:
            root = ET.fromstring(xml_content)
        except ParseError as e:
            raise TopologyParserError(f"Invalid XML content: {e}") from e
        except Exception as e:
            raise TopologyParserError(f"Failed to parse XML content: {e}") from e
        
        return self._parse_root(root)

    def _parse_root(self, root: ET.Element) -> Topology:
        """Parse the root element and create a Topology model.
        
        Args:
            root: Root XML element (<topo>)
            
        Returns:
            Topology model
        """
        topology = Topology()
        
        # Parse devices
        devices_elem = root.find("devices")
        if devices_elem is not None:
            topology.devices = self._parse_devices(devices_elem)
        
        # Parse connections (from lines element)
        lines_elem = root.find("lines")
        if lines_elem is not None:
            topology.connections = self._parse_connections(lines_elem, topology.devices)
        
        return topology

    def _parse_devices(self, devices_elem: ET.Element) -> list[Device]:
        """Parse device elements from XML.
        
        Args:
            devices_elem: <devices> XML element
            
        Returns:
            List of Device models
            
        Raises:
            TopologyParserError: If required attributes are missing
        """
        devices = []
        
        for dev_elem in devices_elem.findall("dev"):
            device = self._parse_device(dev_elem)
            if device:
                devices.append(device)
        
        return devices

    def _parse_device(self, dev_elem: ET.Element) -> Device | None:
        """Parse a single device element.
        
        Args:
            dev_elem: <dev> XML element
            
        Returns:
            Device model or None if parsing fails
            
        Raises:
            TopologyParserError: If required attributes are missing
        """
        # Extract required attributes
        name = dev_elem.get("name")
        if not name:
            raise TopologyParserError("Device element missing required 'name' attribute")
        
        model_str = dev_elem.get("model", "")
        if not model_str:
            raise TopologyParserError(f"Device '{name}' missing required 'model' attribute")
        
        # Parse com_port as integer
        com_port_str = dev_elem.get("com_port", "0")
        try:
            com_port = int(com_port_str)
        except ValueError as e:
            raise TopologyParserError(
                f"Device '{name}' has invalid com_port value: '{com_port_str}'"
            ) from e
        
        # Determine device type from model or extract from device structure
        device_type = self._determine_device_type(model_str, dev_elem)
        
        return Device(
            name=name,
            type=device_type,
            model=model_str,
            com_port=com_port
        )

    def _determine_device_type(self, model: str, dev_elem: ET.Element) -> str:
        """Determine the device type from model string or element structure.
        
        Args:
            model: The device model string
            dev_elem: The device XML element
            
        Returns:
            Device type string
        """
        # Map common models to types
        model_lower = model.lower()
        
        if "router" in model_lower:
            return "Router"
        elif "switch" in model_lower or model_lower.startswith("s"):
            return "Switch"
        elif "cloud" in model_lower:
            return "Cloud"
        elif "firewall" in model_lower:
            return "Firewall"
        else:
            # Use model as type if no specific mapping
            return model

    def _parse_connections(
        self, lines_elem: ET.Element, devices: list[Device]
    ) -> list[Connection]:
        """Parse connection elements from XML.
        
        Note: The sample .topo file has an empty <lines /> element.
        This method handles the <line> elements when they exist.
        
        Args:
            lines_elem: <lines> XML element
            devices: List of existing devices for validation
            
        Returns:
            List of Connection models
            
        Raises:
            TopologyParserError: If connection references non-existent device
        """
        connections = []
        device_names = {d.name for d in devices}
        
        for line_elem in lines_elem.findall("line"):
            connection = self._parse_connection(line_elem, device_names)
            if connection:
                connections.append(connection)
        
        return connections

    def _parse_connection(
        self, line_elem: ET.Element, device_names: set[str]
    ) -> Connection | None:
        """Parse a single connection element.
        
        Args:
            line_elem: <line> XML element
            device_names: Set of valid device names for validation
            
        Returns:
            Connection model or None if parsing fails
            
        Raises:
            TopologyParserError: If connection references non-existent device
        """
        # Extract attributes
        from_device = line_elem.get("from_device", "")
        from_port = line_elem.get("from_port", "")
        to_device = line_elem.get("to_device", "")
        to_port = line_elem.get("to_port", "")
        
        # Validate device references
        if from_device and from_device not in device_names:
            raise TopologyParserError(
                f"Connection references non-existent source device: '{from_device}'"
            )
        
        if to_device and to_device not in device_names:
            raise TopologyParserError(
                f"Connection references non-existent target device: '{to_device}'"
            )
        
        return Connection(
            from_device=from_device,
            from_port=from_port,
            to_device=to_device,
            to_port=to_port
        )
