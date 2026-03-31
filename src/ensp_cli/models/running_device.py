"""Running device model for tracking device processes."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class RunningDevice(BaseModel):
    """Model for a running eNSP device.
    
    Tracks device process information for lifecycle management.
    """
    
    name: str = Field(..., description="Device name")
    device_type: str = Field(..., description="Device type: router/switch/firewall")
    model: str = Field(..., description="Device model (AR2220, S5700, etc.)")
    pid: int = Field(..., description="Windows process ID")
    port: int = Field(..., description="Console port")
    mac_address: str = Field(..., description="Assigned MAC address")
    status: str = Field(default="starting", description="Device status")
    started_at: datetime = Field(default_factory=datetime.now, description="Launch timestamp")
    workspace: Optional[Path] = Field(default=None, description="Working directory")
    source: str = Field(default="cli", description="Source: cli or gui")
    cx: Optional[int] = Field(default=None, description="X coordinate in topology")
    cy: Optional[int] = Field(default=None, description="Y coordinate in topology")
    
    @field_validator("device_type")
    @classmethod
    def validate_device_type(cls, v: str) -> str:
        """Validate device type."""
        allowed = {"router", "switch", "firewall"}
        if v not in allowed:
            raise ValueError(f"device_type must be one of {allowed}")
        return v
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status."""
        allowed = {"starting", "running", "stopped", "error"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v
    
    def to_running(self) -> None:
        """Mark device as running."""
        self.status = "running"
    
    def to_stopped(self) -> None:
        """Mark device as stopped."""
        self.status = "stopped"
    
    def to_error(self, error_msg: str = "") -> None:
        """Mark device as error.
        
        Args:
            error_msg: Optional error message
        """
        self.status = "error"
    
    def is_active(self) -> bool:
        """Check if device is active (starting or running).
        
        Returns:
            True if device is active
        """
        return self.status in ("starting", "running")
    
    def get_uptime_seconds(self) -> float:
        """Get device uptime in seconds.
        
        Returns:
            Uptime in seconds
        """
        return (datetime.now() - self.started_at).total_seconds()
    
    def get_uptime_str(self) -> str:
        """Get formatted uptime string.
        
        Returns:
            Uptime as HH:MM:SS
        """
        seconds = int(self.get_uptime_seconds())
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
