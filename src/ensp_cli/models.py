"""Data models for eNSP topology."""

from pydantic import BaseModel, Field


class Device(BaseModel):
    """Represents a device in the topology."""

    name: str = Field(..., description="Device identifier")
    type: str = Field(..., description="Device category (Router, Switch, etc.)")
    model: str = Field(..., description="Specific hardware model")
    com_port: int = Field(..., description="Console port for Telnet access")


class Connection(BaseModel):
    """Represents a connection between two devices."""

    from_device: str = Field(..., description="Source device name")
    from_port: str = Field(..., description="Source interface")
    to_device: str = Field(..., description="Target device name")
    to_port: str = Field(..., description="Target interface")


class Topology(BaseModel):
    """Represents an eNSP topology."""

    devices: list[Device] = Field(default_factory=list, description="List of devices")
    connections: list[Connection] = Field(default_factory=list, description="List of connections")
