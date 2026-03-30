"""Secure XML parser for eNSP topology files."""

from pathlib import Path
from xml.etree.ElementTree import Element

import defusedxml.ElementTree as ET
from defusedxml.ElementTree import ParseError

from ensp_cli.models import Connection, Device, Topology


class TopologyParserError(Exception):
    """Base exception for topology parser errors."""
    pass


class TopologyParser:
    """Parser for eNSP .topo topology files using secure XML parsing.
    
    Uses defusedxml to prevent XXE attacks and XML bomb vulnerabilities.
    Handles UTF-8 encoded eNSP files which declare "UNICODE" encoding.
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
        
        # Get topology name from filename (without extension)
        topology_name = file_path.stem
        
        try:
            # eNSP files are typically UTF-8 encoded but declare "UNICODE"
            # We read as UTF-8 and let defusedxml handle the parsing
            content = file_path.read_text(encoding="utf-8")
            root = ET.fromstring(content)
        except ParseError as e:
            raise TopologyParserError(f"Invalid XML in topology file: {e}") from e
        except Exception as e:
            raise TopologyParserError(f"Failed to parse topology file: {e}") from e
        
        return self._parse_root(root, topology_name, file_path)

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
        
        return self._parse_root(root, "unnamed", None)

    def _parse_root(self, root: Element, topology_name: str, file_path: Path | None) -> Topology:
        """Parse the root element and create a Topology model.
        
        Args:
            root: Root XML element (<topo>)
            topology_name: Name for the topology
            file_path: Optional path to the source file
            
        Returns:
            Topology model
        """
        topology = Topology(name=topology_name, file_path=file_path)
        
        # Parse devices first and build ID -> name mapping
        devices_elem = root.find("devices")
        device_id_map = {}
        if devices_elem is not None:
            devices = self._parse_devices(devices_elem)
            for device in devices:
                if device:  # Skip None devices
                    topology.add_device(device)
                    # Build mapping from XML id to device name for connections
                    dev_elem = devices_elem.find(f".//dev[@name='{device.name}']")
                    if dev_elem is not None:
                        device_id = dev_elem.get("id", "")
                        if device_id:
                            device_id_map[device_id] = device.name
        
        # Parse connections (from lines element)
        lines_elem = root.find("lines")
        if lines_elem is not None:
            connections = self._parse_connections(lines_elem, device_id_map)
            for connection in connections:
                topology.add_connection(connection)
        
        return topology

    def _parse_devices(self, devices_elem: Element) -> list[Device]:
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

    def _parse_device(self, dev_elem: Element) -> Device | None:
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
        
        # Parse com_port as integer (mapping to console_port in model)
        com_port_str = dev_elem.get("com_port", "0")
        try:
            com_port = int(com_port_str)
        except ValueError as e:
            raise TopologyParserError(
                f"Device '{name}' has invalid com_port value: '{com_port_str}'"
            ) from e
        
        # Determine device type from model string
        device_type = self._determine_device_type(model_str)
        
        # For Cloud devices (com_port=0), we still include them with console_port=1
        # This is a workaround since the model requires valid port range (1-65535)
        console_port = com_port if com_port >= 1 else 1
        
        return Device(
            name=name,
            device_type=device_type,
            model=model_str,
            console_port=console_port
        )

    def _determine_device_type(self, model: str) -> str:
        """Determine the device type from model string.
        
        Args:
            model: The device model string
            
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
        elif "firewall" in model_lower or model_lower.startswith("usg"):
            return "Firewall"
        else:
            # Use model as type if no specific mapping
            return model

    def _parse_connections(self, lines_elem: Element, device_id_map: dict[str, str]) -> list[Connection]:
        """Parse connection elements from XML.
        
        Args:
            lines_elem: <lines> XML element
            device_id_map: Mapping from device XML id to device name
            
        Returns:
            List of Connection models
        """
        connections = []
        
        for line_elem in lines_elem.findall("line"):
            connection = self._parse_connection(line_elem, device_id_map)
            if connection:
                connections.append(connection)
        
        return connections

    def _parse_connection(self, line_elem: Element, device_id_map: dict[str, str]) -> Connection | None:
        """Parse a single connection element.
        
        Args:
            line_elem: <line> XML element
            device_id_map: Mapping from device XML id to device name
            
        Returns:
            Connection model or None if parsing fails
        """
        # eNSP uses srcDeviceID and destDeviceID attributes
        src_id = line_elem.get("srcDeviceID", "")
        dest_id = line_elem.get("destDeviceID", "")
        
        # Map IDs to device names
        from_device = device_id_map.get(src_id, "")
        to_device = device_id_map.get(dest_id, "")
        
        # Skip if we can't map to device names
        if not from_device or not to_device:
            return None
        
        # Extract interface info from interfacePair child element
        from_port = ""
        to_port = ""
        interface_pair = line_elem.find("interfacePair")
        if interface_pair is not None:
            # srcIndex and tarIndex refer to interface indices
            src_idx = interface_pair.get("srcIndex", "")
            tar_idx = interface_pair.get("tarIndex", "")
            # lineName indicates the type (Copper, Serial, etc.)
            line_type = interface_pair.get("lineName", "")
            from_port = f"{line_type}:{src_idx}" if line_type else src_idx
            to_port = f"{line_type}:{tar_idx}" if line_type else tar_idx
        
        return Connection(
            from_device=from_device,
            from_port=from_port,
            to_device=to_device,
            to_port=to_port
        )
