"""Pydantic models for eNSP topology domain entities."""

from pydantic import BaseModel, Field


class Device(BaseModel):
    """Represents a device in the topology.
    
    Attributes:
        name: Device identifier (e.g., "R1", "LSW1")
        type: Device category (e.g., "Router", "S5700", "Cloud")
        model: Specific hardware model string
        com_port: Console port number for Telnet access (0 if not applicable)
    """

    name: str = Field(..., description="Device identifier")
    type: str = Field(..., description="Device category (Router, Switch, etc.)")
    model: str = Field(..., description="Specific hardware model")
    com_port: int = Field(..., description="Console port for Telnet access")


class Connection(BaseModel):
    """Represents a connection between two devices.
    
    Attributes:
        from_device: Source device name
        from_port: Source interface (e.g., "GE0/0/1", "Ethernet0/0/0")
        to_device: Target device name
        to_port: Target interface
    """

    from_device: str = Field(..., description="Source device name")
    from_port: str = Field(..., description="Source interface")
    to_device: str = Field(..., description="Target device name")
    to_port: str = Field(..., description="Target interface")


class Topology(BaseModel):
    """Represents an eNSP topology file contents.
    
    Attributes:
        devices: List of devices in the topology
        connections: List of connections between devices
    """

    devices: list[Device] = Field(default_factory=list, description="List of devices")
    connections: list[Connection] = Field(default_factory=list, description="List of connections")
