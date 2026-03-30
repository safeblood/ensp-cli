"""Topology model for eNSP topology entities."""

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from .connection import Connection
from .device import Device


class Topology(BaseModel):
    """Represents an eNSP topology containing devices and connections.
    
    This is the aggregate root for the topology domain.
    
    Attributes:
        name: Topology name from filename or XML.
        devices: List of devices in the topology.
        connections: List of connections between devices.
        file_path: Path to the source .topo file (optional).
    """
    
    name: str = Field(..., description="Topology name from filename or XML")
    devices: List[Device] = Field(default_factory=list, description="List of devices")
    connections: List[Connection] = Field(default_factory=list, description="List of connections")
    file_path: Optional[Path] = Field(default=None, description="Source .topo file path")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is a non-empty string."""
        if not v or not v.strip():
            raise ValueError("Topology name must be a non-empty string")
        return v.strip()
    
    @property
    def device_count(self) -> int:
        """Return the number of devices in the topology."""
        return len(self.devices)
    
    @property
    def connection_count(self) -> int:
        """Return the number of connections in the topology."""
        return len(self.connections)
    
    def get_device(self, name: str) -> Optional[Device]:
        """Find a device by name.
        
        Args:
            name: The device name to search for.
            
        Returns:
            The Device if found, None otherwise.
        """
        for device in self.devices:
            if device.name == name:
                return device
        return None
    
    def get_connections_for(self, device_name: str) -> List[Connection]:
        """Get all connections involving a specific device.
        
        Args:
            device_name: The name of the device.
            
        Returns:
            List of connections where the device is either source or target.
        """
        return [
            conn for conn in self.connections
            if conn.involves_device(device_name)
        ]
    
    def add_device(self, device: Device) -> None:
        """Add a device to the topology.
        
        Args:
            device: The device to add.
            
        Raises:
            ValueError: If a device with the same name already exists.
        """
        if self.get_device(device.name) is not None:
            raise ValueError(f"Device '{device.name}' already exists in topology")
        self.devices.append(device)
    
    def add_connection(self, connection: Connection) -> None:
        """Add a connection to the topology.
        
        Args:
            connection: The connection to add.
            
        Raises:
            ValueError: If either device in the connection doesn't exist.
        """
        if self.get_device(connection.from_device) is None:
            raise ValueError(f"Source device '{connection.from_device}' not found in topology")
        if self.get_device(connection.to_device) is None:
            raise ValueError(f"Target device '{connection.to_device}' not found in topology")
        self.connections.append(connection)
    
    def __str__(self) -> str:
        """Return string representation of the topology."""
        return f"Topology('{self.name}': {self.device_count} devices, {self.connection_count} connections)"
    
    def __repr__(self) -> str:
        """Return detailed representation of the topology."""
        return (
            f"Topology(name='{self.name}', devices={self.devices}, "
            f"connections={self.connections}, file_path={self.file_path})"
        )
