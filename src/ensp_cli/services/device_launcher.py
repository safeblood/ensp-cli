"""Device launcher service for eNSP devices."""

import asyncio
import subprocess
from pathlib import Path
from typing import Optional

from ensp_cli.services.mac_generator import MacGenerator
from ensp_cli.services.port_allocator import PortAllocator


class DeviceLauncher:
    """Launch eNSP router and switch devices."""
    
    # eNSP installation paths
    ENSP_BASE_PATH = Path("C:/Program Files/Huawei/eNSP/vboxserver/devices")
    
    DEVICE_EXECUTABLES = {
        "AR2220": ENSP_BASE_PATH / "AR" / "AR" / "eNSP_Router.exe",
        "AR3260": ENSP_BASE_PATH / "AR" / "AR" / "eNSP_Router.exe",
        "S3700": ENSP_BASE_PATH / "LSW" / "s3700" / "eNSP_Switch.exe",
        "S5700": ENSP_BASE_PATH / "LSW" / "s5700" / "eNSP_Switch.exe",
    }
    
    def __init__(
        self,
        mac_generator: Optional[MacGenerator] = None,
        port_allocator: Optional[PortAllocator] = None
    ) -> None:
        """Initialize the device launcher.
        
        Args:
            mac_generator: MAC address generator (creates default if None)
            port_allocator: Port allocator (creates default if None)
        """
        self._mac_gen = mac_generator or MacGenerator()
        self._port_alloc = port_allocator or PortAllocator()
    
    def launch_router(
        self,
        name: str,
        model: str = "AR2220",
        port: Optional[int] = None
    ) -> dict:
        """Launch a router device.
        
        Args:
            name: Device name
            model: Router model (AR2220, AR3260)
            port: Console port (auto-allocated if None)
            
        Returns:
            Dictionary with launch info:
            - pid: Process ID
            - port: Console port
            - mac: MAC address
            - name: Device name
            - model: Device model
            
        Raises:
            ValueError: If model is not supported
            RuntimeError: If launch fails after retries
        """
        if model not in self.DEVICE_EXECUTABLES:
            raise ValueError(f"Unsupported router model: {model}")
        
        return self._launch_device(name, model, "router", port)
    
    def launch_switch(
        self,
        name: str,
        model: str = "S5700",
        port: Optional[int] = None
    ) -> dict:
        """Launch a switch device.
        
        Args:
            name: Device name
            model: Switch model (S3700, S5700)
            port: Console port (auto-allocated if None)
            
        Returns:
            Dictionary with launch info
            
        Raises:
            ValueError: If model is not supported
            RuntimeError: If launch fails after retries
        """
        if model not in self.DEVICE_EXECUTABLES:
            raise ValueError(f"Unsupported switch model: {model}")
        
        return self._launch_device(name, model, "switch", port)
    
    def _launch_device(
        self,
        name: str,
        model: str,
        device_type: str,
        port: Optional[int] = None,
        max_retries: int = 3
    ) -> dict:
        """Launch a device with retry logic.
        
        Args:
            name: Device name
            model: Device model
            device_type: 'router' or 'switch'
            port: Console port (auto-allocated if None)
            max_retries: Maximum retry attempts
            
        Returns:
            Dictionary with launch info
            
        Raises:
            RuntimeError: If all retries fail
        """
        last_error: Optional[Exception] = None
        
        for attempt in range(1, max_retries + 1):
            try:
                return self._try_launch(name, model, device_type, port)
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    asyncio.run(asyncio.sleep(2))  # Wait before retry
        
        raise RuntimeError(
            f"Failed to launch {name} after {max_retries} attempts: {last_error}"
        )
    
    def _try_launch(
        self,
        name: str,
        model: str,
        device_type: str,
        port: Optional[int] = None
    ) -> dict:
        """Try to launch a device.
        
        Args:
            name: Device name
            model: Device model
            device_type: 'router' or 'switch'
            port: Console port (auto-allocated if None)
            
        Returns:
            Dictionary with launch info
        """
        # Allocate port
        allocated_port = self._port_alloc.allocate(port)
        
        try:
            # Generate MAC address
            mac = self._mac_gen.generate(device_type)
            
            # Get executable path
            exe_path = self.DEVICE_EXECUTABLES[model]
            
            if not exe_path.exists():
                raise RuntimeError(f"eNSP executable not found: {exe_path}")
            
            # Build command
            cmd = [
                str(exe_path),
                "sim",
                f"system_mac={mac}",
                name
            ]
            
            # Start process (hidden window to avoid popup)
            # Note: eNSP devices use environment variables for port configuration
            # The port is typically set via VBOX_ environment or detected by eNSP
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            return {
                "pid": process.pid,
                "port": allocated_port,
                "mac": mac,
                "name": name,
                "model": model,
                "device_type": device_type,
            }
            
        except Exception:
            # Release port on failure
            self._port_alloc.release(allocated_port)
            raise
    
    async def wait_for_ready(
        self,
        port: int,
        timeout: int = 30,
        poll_interval: float = 1.0
    ) -> dict:
        """Wait for device to be ready (Telnet accessible).
        
        Args:
            port: Console port to check
            timeout: Maximum wait time in seconds
            poll_interval: Time between polls
            
        Returns:
            Dictionary with ready status and time taken
        """
        import telnetlib3
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            
            if elapsed > timeout:
                return {
                    "ready": False,
                    "time_taken": elapsed,
                    "error": "Timeout waiting for device",
                }
            
            try:
                # Try to connect
                reader, writer = await asyncio.wait_for(
                    telnetlib3.open_connection("127.0.0.1", port),
                    timeout=2.0
                )
                writer.close()
                await writer.wait_closed()
                
                return {
                    "ready": True,
                    "time_taken": elapsed,
                }
                
            except (OSError, asyncio.TimeoutError):
                await asyncio.sleep(poll_interval)
    
    def release_port(self, port: int) -> None:
        """Release an allocated port.
        
        Args:
            port: Port to release
        """
        self._port_alloc.release(port)
    
    def release_mac(self, mac: str) -> None:
        """Release a MAC address.
        
        Args:
            mac: MAC address to release
        """
        self._mac_gen.release(mac)


# Global instance for convenience
_default_launcher: DeviceLauncher | None = None


def get_launcher() -> DeviceLauncher:
    """Get the default device launcher instance."""
    global _default_launcher
    if _default_launcher is None:
        _default_launcher = DeviceLauncher()
    return _default_launcher
