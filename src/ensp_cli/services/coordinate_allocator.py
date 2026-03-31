"""Coordinate allocator for eNSP device positioning in topology."""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple


class CoordinateAllocator:
    """Allocate (cx, cy) coordinates for devices in eNSP topology.
    
    Ensures devices appear at proper positions in GUI without overlap.
    Uses grid layout with configurable spacing.
    """
    
    DEFAULT_GRID_SIZE = 100
    DEFAULT_START_X = 100
    DEFAULT_START_Y = 100
    
    def __init__(
        self,
        grid_size: int = DEFAULT_GRID_SIZE,
        start_x: int = DEFAULT_START_X,
        start_y: int = DEFAULT_START_Y
    ) -> None:
        """Initialize the coordinate allocator.
        
        Args:
            grid_size: Grid spacing in pixels
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
        """
        self._grid_size = grid_size
        self._start_x = start_x
        self._start_y = start_y
    
    def allocate(
        self,
        topo_path: Optional[Path] = None,
        custom_x: Optional[int] = None,
        custom_y: Optional[int] = None
    ) -> Tuple[int, int]:
        """Allocate coordinates for a new device.
        
        Args:
            topo_path: Path to topology file (for auto-calculation)
            custom_x: Override X coordinate (optional)
            custom_y: Override Y coordinate (optional)
            
        Returns:
            (cx, cy) tuple
        """
        # Use custom coordinates if provided
        if custom_x is not None and custom_y is not None:
            return (custom_x, custom_y)
        
        # Calculate from topology if available
        if topo_path and topo_path.exists():
            return self._calculate_from_topology(topo_path)
        
        # Default position
        return (self._start_x, self._start_y)
    
    def _calculate_from_topology(self, topo_path: Path) -> Tuple[int, int]:
        """Calculate next available position based on existing devices.
        
        Args:
            topo_path: Path to topology file
            
        Returns:
            (cx, cy) tuple for new device
        """
        try:
            tree = ET.parse(topo_path)
            root = tree.getroot()
            
            # Find all device positions
            positions = []
            for device in root.findall(".//dev"):
                cx = device.get("cx")
                cy = device.get("cy")
                if cx is not None and cy is not None:
                    try:
                        positions.append((int(cx), int(cy)))
                    except ValueError:
                        continue
            
            if not positions:
                return (self._start_x, self._start_y)
            
            # Find bounding box
            max_x = max(pos[0] for pos in positions)
            max_y = max(pos[1] for pos in positions)
            min_x = min(pos[0] for pos in positions)
            
            # Place to the right of existing devices
            # If too far right, wrap to next row
            new_x = max_x + self._grid_size
            new_y = max_y
            
            # If exceeds reasonable width (e.g., 800px), start new row
            if new_x > 800:
                new_x = self._start_x
                new_y = max_y + self._grid_size
            
            return (new_x, new_y)
            
        except (ET.ParseError, OSError):
            # If parsing fails, use default
            return (self._start_x, self._start_y)
    
    def get_device_positions(self, topo_path: Path) -> list[Tuple[int, int]]:
        """Get all device positions from topology file.
        
        Args:
            topo_path: Path to topology file
            
        Returns:
            List of (cx, cy) tuples
        """
        positions = []
        
        try:
            tree = ET.parse(topo_path)
            root = tree.getroot()
            
            for device in root.findall(".//dev"):
                cx = device.get("cx")
                cy = device.get("cy")
                if cx is not None and cy is not None:
                    try:
                        positions.append((int(cx), int(cy)))
                    except ValueError:
                        continue
        except (ET.ParseError, OSError):
            pass
        
        return positions
    
    def would_overlap(
        self,
        topo_path: Path,
        cx: int,
        cy: int,
        threshold: int = 50
    ) -> bool:
        """Check if a position would overlap with existing devices.
        
        Args:
            topo_path: Path to topology file
            cx: Proposed X coordinate
            cy: Proposed Y coordinate
            threshold: Minimum distance to avoid overlap
            
        Returns:
            True if position would overlap
        """
        positions = self.get_device_positions(topo_path)
        
        for pos_x, pos_y in positions:
            distance = ((cx - pos_x) ** 2 + (cy - pos_y) ** 2) ** 0.5
            if distance < threshold:
                return True
        
        return False


# Global instance for convenience
_default_allocator: CoordinateAllocator | None = None


def get_allocator() -> CoordinateAllocator:
    """Get the default coordinate allocator instance."""
    global _default_allocator
    if _default_allocator is None:
        _default_allocator = CoordinateAllocator()
    return _default_allocator


def allocate_coordinates(
    topo_path: Optional[Path] = None,
    custom_x: Optional[int] = None,
    custom_y: Optional[int] = None
) -> Tuple[int, int]:
    """Allocate coordinates using the default allocator.
    
    Args:
        topo_path: Path to topology file
        custom_x: Override X coordinate
        custom_y: Override Y coordinate
        
    Returns:
        (cx, cy) tuple
    """
    return get_allocator().allocate(topo_path, custom_x, custom_y)
