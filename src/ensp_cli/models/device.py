"""Device model for eNSP topology entities."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Device(BaseModel):
    """Represents a network device in eNSP topology.
    
    Attributes:
        name: Device identifier from XML.
        device_type: Type of device (e.g., "Router", "Switch", "Firewall").
        model: Device model (e.g., "AR2220", "S5700").
        console_port: Telnet port number for console access.
        x: X coordinate from XML (cx attribute) for visual layout.
        y: Y coordinate from XML (cy attribute) for visual layout.
    """
    
    name: str = Field(..., description="Device identifier from XML")
    device_type: str = Field(..., description="Device type (e.g., Router, Switch, Firewall)")
    model: str = Field(..., description="Device model (e.g., AR2220, S5700)")
    console_port: int = Field(..., description="Telnet port number for console access")
    x: Optional[float] = Field(default=None, description="X coordinate for visual layout")
    y: Optional[float] = Field(default=None, description="Y coordinate for visual layout")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is a non-empty string."""
        if not v or not v.strip():
            raise ValueError("Device name must be a non-empty string")
        return v.strip()
    
    @field_validator("device_type")
    @classmethod
    def validate_device_type(cls, v: str) -> str:
        """Validate that device_type is a non-empty string."""
        if not v or not v.strip():
            raise ValueError("Device type must be a non-empty string")
        return v.strip()
    
    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate that model is a non-empty string."""
        if not v or not v.strip():
            raise ValueError("Device model must be a non-empty string")
        return v.strip()
    
    @field_validator("console_port")
    @classmethod
    def validate_console_port(cls, v: int) -> int:
        """Validate that console_port is within valid port range (1-65535)."""
        if v < 1 or v > 65535:
            raise ValueError("Console port must be between 1 and 65535")
        return v
    
    def __str__(self) -> str:
        """Return string representation of the device."""
        return f"{self.name} ({self.device_type}/{self.model}, console={self.console_port})"
    
    def __repr__(self) -> str:
        """Return detailed representation of the device."""
        return (
            f"Device(name='{self.name}', device_type='{self.device_type}', "
            f"model='{self.model}', console_port={self.console_port})"
        )
