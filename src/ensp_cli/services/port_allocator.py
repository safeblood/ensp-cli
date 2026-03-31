"""Port allocator for eNSP device console connections."""

import socket
import subprocess
import threading
from typing import Optional, Set


class PortAllocator:
    """Allocate console ports for eNSP devices.
    
    Manages port range 2000-2100, detects GUI device ports,
    and ensures thread-safe allocation.
    """
    
    DEFAULT_START = 2000
    DEFAULT_END = 2100
    
    def __init__(self, start: int = DEFAULT_START, end: int = DEFAULT_END) -> None:
        """Initialize the port allocator.
        
        Args:
            start: Start of port range (inclusive)
            end: End of port range (inclusive)
        """
        self._start = start
        self._end = end
        self._allocated: Set[int] = set()
        self._lock = threading.Lock()
    
    def allocate(self, preferred_port: Optional[int] = None) -> int:
        """Allocate an available port.
        
        Args:
            preferred_port: Specific port to try first (if available)
            
        Returns:
            Allocated port number
            
        Raises:
            RuntimeError: If no ports available
        """
        with self._lock:
            # Get ports used by GUI devices
            gui_ports = self._detect_gui_ports()
            
            # Try preferred port first
            if preferred_port is not None:
                if self._is_available(preferred_port, gui_ports):
                    self._allocated.add(preferred_port)
                    return preferred_port
            
            # Find first available port
            for port in range(self._start, self._end + 1):
                if self._is_available(port, gui_ports):
                    self._allocated.add(port)
                    return port
            
            raise RuntimeError(
                f"No available ports in range {self._start}-{self._end}. "
                f"GUI ports in use: {gui_ports}, "
                f"CLI allocated: {self._allocated}"
            )
    
    def release(self, port: int) -> None:
        """Release a previously allocated port.
        
        Args:
            port: Port to release
        """
        with self._lock:
            self._allocated.discard(port)
    
    def is_allocated(self, port: int) -> bool:
        """Check if a port is allocated by this allocator.
        
        Args:
            port: Port to check
            
        Returns:
            True if port is allocated
        """
        with self._lock:
            return port in self._allocated
    
    def get_allocated_ports(self) -> Set[int]:
        """Get all allocated ports.
        
        Returns:
            Set of allocated port numbers
        """
        with self._lock:
            return self._allocated.copy()
    
    def _is_available(self, port: int, gui_ports: Set[int]) -> bool:
        """Check if a port is available.
        
        Args:
            port: Port to check
            gui_ports: Set of ports used by GUI-launched devices
            
        Returns:
            True if port is available
        """
        # Check if in valid range
        if not (self._start <= port <= self._end):
            return False
        
        # Check if already allocated by us
        if port in self._allocated:
            return False
        
        # Check if used by GUI
        if port in gui_ports:
            return False
        
        # Try to bind to verify it's actually free
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", port))
                return True
        except OSError:
            return False
    
    def _detect_gui_ports(self) -> Set[int]:
        """Detect ports used by GUI-launched eNSP devices.
        
        Scans for eNSP_Router.exe and eNSP_Switch.exe processes
        and extracts their console ports.
        
        Returns:
            Set of ports used by GUI devices
        """
        gui_ports: Set[int] = set()
        
        try:
            # Use netstat to find listening ports for eNSP processes
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                encoding="gbk",
                errors="ignore"
            )
            
            # Get PIDs of eNSP device processes
            pids = self._get_ensp_pids()
            
            # Parse netstat output
            for line in result.stdout.splitlines():
                # Look for lines with LISTENING state and matching PIDs
                if "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        # Extract port from local address (e.g., "127.0.0.1:2000")
                        local_addr = parts[1]
                        if ":" in local_addr:
                            try:
                                port = int(local_addr.split(":")[-1])
                                pid = int(parts[-1])
                                
                                # Check if this PID belongs to eNSP device
                                if pid in pids and self._start <= port <= self._end:
                                    gui_ports.add(port)
                            except ValueError:
                                continue
        except Exception:
            # If detection fails, return empty set
            pass
        
        return gui_ports
    
    def _get_ensp_pids(self) -> Set[int]:
        """Get PIDs of eNSP device processes.
        
        Returns:
            Set of process IDs
        """
        pids: Set[int] = set()
        
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq eNSP_Router.exe", "/FO", "CSV"],
                capture_output=True,
                text=True,
                encoding="gbk",
                errors="ignore"
            )
            pids.update(self._parse_tasklist_csv(result.stdout))
            
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq eNSP_Switch.exe", "/FO", "CSV"],
                capture_output=True,
                text=True,
                encoding="gbk",
                errors="ignore"
            )
            pids.update(self._parse_tasklist_csv(result.stdout))
        except Exception:
            pass
        
        return pids
    
    def _parse_tasklist_csv(self, output: str) -> Set[int]:
        """Parse tasklist CSV output to extract PIDs.
        
        Args:
            output: CSV output from tasklist
            
        Returns:
            Set of PIDs
        """
        pids: Set[int] = set()
        
        lines = output.strip().splitlines()
        for line in lines[1:]:  # Skip header
            parts = line.split('","')
            if len(parts) >= 2:
                try:
                    pid = int(parts[1].replace('"', ''))
                    pids.add(pid)
                except ValueError:
                    continue
        
        return pids


# Global instance for convenience
_default_allocator: PortAllocator | None = None


def get_allocator() -> PortAllocator:
    """Get the default port allocator instance."""
    global _default_allocator
    if _default_allocator is None:
        _default_allocator = PortAllocator()
    return _default_allocator


def allocate_port(preferred_port: Optional[int] = None) -> int:
    """Allocate a port using the default allocator.
    
    Args:
        preferred_port: Specific port to try first
        
    Returns:
        Allocated port number
    """
    return get_allocator().allocate(preferred_port)
