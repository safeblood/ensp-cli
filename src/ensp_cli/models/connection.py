"""Connection model for eNSP topology entities."""

from pydantic import BaseModel, Field, model_validator


class Connection(BaseModel):
    """Represents a connection between two devices in eNSP topology.
    
    Attributes:
        from_device: Source device name.
        from_port: Source interface (e.g., "GE0/0/0").
        to_device: Target device name.
        to_port: Target interface (e.g., "GE0/0/1").
    """
    
    from_device: str = Field(..., description="Source device name")
    from_port: str = Field(..., description="Source interface (e.g., GE0/0/0)")
    to_device: str = Field(..., description="Target device name")
    to_port: str = Field(..., description="Target interface (e.g., GE0/0/1)")
    
    @model_validator(mode="after")
    def validate_devices_not_same(self) -> "Connection":
        """Validate that from_device and to_device are not the same."""
        if self.from_device.strip() == self.to_device.strip():
            raise ValueError("Source and target devices cannot be the same")
        return self
    
    @model_validator(mode="after")
    def validate_non_empty_fields(self) -> "Connection":
        """Validate that all string fields are non-empty."""
        if not self.from_device or not self.from_device.strip():
            raise ValueError("Source device name must be non-empty")
        if not self.from_port or not self.from_port.strip():
            raise ValueError("Source port must be non-empty")
        if not self.to_device or not self.to_device.strip():
            raise ValueError("Target device name must be non-empty")
        if not self.to_port or not self.to_port.strip():
            raise ValueError("Target port must be non-empty")
        return self
    
    def __str__(self) -> str:
        """Return string representation of the connection."""
        return f"{self.from_device}:{self.from_port} -> {self.to_device}:{self.to_port}"
    
    def __repr__(self) -> str:
        """Return detailed representation of the connection."""
        return (
            f"Connection(from_device='{self.from_device}', from_port='{self.from_port}', "
            f"to_device='{self.to_device}', to_port='{self.to_port}')"
        )
    
    def involves_device(self, device_name: str) -> bool:
        """Check if this connection involves the given device.
        
        Args:
            device_name: Name of the device to check.
            
        Returns:
            True if the connection involves the device, False otherwise.
        """
        return self.from_device == device_name or self.to_device == device_name
