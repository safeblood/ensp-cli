"""MAC address generator for Huawei eNSP devices."""

import random
from typing import Set


class MacGenerator:
    """Generate unique MAC addresses for eNSP devices.
    
    Uses Huawei OUIs:
    - Routers: 54-89-98
    - Switches: 4C-1F-CC
    """
    
    # Huawei OUIs for different device types
    OUIS = {
        "router": "54-89-98",
        "switch": "4C-1F-CC",
    }
    
    def __init__(self) -> None:
        """Initialize the MAC generator."""
        self._used_macs: Set[str] = set()
    
    def generate(self, device_type: str = "router") -> str:
        """Generate a unique MAC address.
        
        Args:
            device_type: Type of device ('router' or 'switch')
            
        Returns:
            MAC address in format XX-XX-XX-XX-XX-XX
            
        Raises:
            ValueError: If device type is not supported
            RuntimeError: If unable to generate unique MAC after max attempts
        """
        if device_type not in self.OUIS:
            raise ValueError(f"Unsupported device type: {device_type}. "
                           f"Supported: {list(self.OUIS.keys())}")
        
        oui = self.OUIS[device_type]
        max_attempts = 100
        
        for _ in range(max_attempts):
            # Generate random last 3 bytes
            last_bytes = [random.randint(0x00, 0xFF) for _ in range(3)]
            last_part = "-".join(f"{b:02X}" for b in last_bytes)
            
            mac = f"{oui}-{last_part}"
            
            if mac not in self._used_macs:
                self._used_macs.add(mac)
                return mac
        
        raise RuntimeError(f"Failed to generate unique MAC after {max_attempts} attempts")
    
    def release(self, mac: str) -> None:
        """Release a MAC address back to the pool.
        
        Args:
            mac: MAC address to release
        """
        self._used_macs.discard(mac)
    
    def is_used(self, mac: str) -> bool:
        """Check if a MAC address is already used.
        
        Args:
            mac: MAC address to check
            
        Returns:
            True if MAC is in use
        """
        return mac in self._used_macs
    
    def get_used_count(self) -> int:
        """Get count of used MAC addresses.
        
        Returns:
            Number of MAC addresses currently in use
        """
        return len(self._used_macs)
    
    def clear(self) -> None:
        """Clear all used MAC addresses."""
        self._used_macs.clear()


# Global instance for convenience
_default_generator: MacGenerator | None = None


def get_generator() -> MacGenerator:
    """Get the default MAC generator instance."""
    global _default_generator
    if _default_generator is None:
        _default_generator = MacGenerator()
    return _default_generator


def generate_mac(device_type: str = "router") -> str:
    """Generate a MAC address using the default generator.
    
    Args:
        device_type: Type of device ('router' or 'switch')
        
    Returns:
        MAC address in format XX-XX-XX-XX-XX-XX
    """
    return get_generator().generate(device_type)
