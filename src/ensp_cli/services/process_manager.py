"""Process manager for tracking and managing running devices."""

import json
import subprocess
from pathlib import Path
from typing import Optional

from ensp_cli.models.running_device import RunningDevice


class ProcessManager:
    """Manage running device processes.
    
    Tracks device state, persists to JSON file, and provides
    process control (stop, monitor, etc.).
    """
    
    DEFAULT_STATE_DIR = Path.home() / ".ensp"
    DEFAULT_STATE_FILE = DEFAULT_STATE_DIR / "running_devices.json"
    
    def __init__(self, state_file: Optional[Path] = None) -> None:
        """Initialize the process manager.
        
        Args:
            state_file: Path to state file (uses default if None)
        """
        self._state_file = state_file or self.DEFAULT_STATE_FILE
        self._devices: dict[str, RunningDevice] = {}
        self._load_state()
    
    def register_device(self, device: RunningDevice) -> None:
        """Register a running device.
        
        Args:
            device: Device to register
        """
        self._devices[device.name] = device
        self._save_state()
    
    def unregister_device(self, name: str) -> Optional[RunningDevice]:
        """Unregister a device.
        
        Args:
            name: Device name
            
        Returns:
            The unregistered device, or None if not found
        """
        device = self._devices.pop(name, None)
        if device:
            self._save_state()
        return device
    
    def get_device(self, name: str) -> Optional[RunningDevice]:
        """Get a device by name.
        
        Args:
            name: Device name
            
        Returns:
            Device if found, None otherwise
        """
        return self._devices.get(name)
    
    def list_devices(
        self,
        refresh: bool = False,
        active_only: bool = False
    ) -> list[RunningDevice]:
        """List all tracked devices.
        
        Args:
            refresh: Refresh status before listing
            active_only: Only return active devices
            
        Returns:
            List of devices
        """
        if refresh:
            self.refresh_status()
        
        devices = list(self._devices.values())
        
        if active_only:
            devices = [d for d in devices if d.is_active()]
        
        return devices
    
    def stop_device(self, name: str, force: bool = False) -> dict:
        """Stop a device.
        
        Args:
            name: Device name
            force: Force kill if graceful stop fails
            
        Returns:
            Dictionary with stop result:
            - success: True if stopped successfully
            - message: Status message
            - was_running: Whether device was running before stop
        """
        device = self.get_device(name)
        
        if not device:
            return {
                "success": False,
                "message": f"Device '{name}' not found",
                "was_running": False,
            }
        
        was_running = device.is_active()
        
        if not was_running:
            self.unregister_device(name)
            return {
                "success": True,
                "message": f"Device '{name}' was already stopped",
                "was_running": False,
            }
        
        # Try graceful stop first
        if not force:
            result = self._graceful_stop(device.pid)
            if result:
                device.to_stopped()
                self.unregister_device(name)
                return {
                    "success": True,
                    "message": f"Device '{name}' stopped gracefully",
                    "was_running": True,
                }
        
        # Force stop
        result = self._force_stop(device.pid)
        if result:
            device.to_stopped()
            self.unregister_device(name)
            return {
                "success": True,
                "message": f"Device '{name}' force stopped",
                "was_running": True,
            }
        
        return {
            "success": False,
            "message": f"Failed to stop device '{name}'",
            "was_running": True,
        }
    
    def stop_all(self, force: bool = False) -> list[dict]:
        """Stop all devices.
        
        Args:
            force: Force kill all devices
            
        Returns:
            List of stop results
        """
        results = []
        for name in list(self._devices.keys()):
            results.append(self.stop_device(name, force))
        return results
    
    def refresh_status(self) -> list[RunningDevice]:
        """Refresh status of all devices.
        
        Checks if processes are still running and updates status.
        Removes entries for processes that have died.
        
        Returns:
            List of devices with updated status
        """
        to_remove = []
        
        for name, device in self._devices.items():
            if not self._is_process_running(device.pid):
                if device.is_active():
                    # Process died unexpectedly
                    device.to_error("Process terminated unexpectedly")
                    to_remove.append(name)
        
        # Clean up dead processes
        for name in to_remove:
            self.unregister_device(name)
        
        return self.list_devices()
    
    def _graceful_stop(self, pid: int, timeout: int = 5) -> bool:
        """Try to gracefully stop a process.
        
        Args:
            pid: Process ID
            timeout: Seconds to wait
            
        Returns:
            True if process stopped
        """
        try:
            # On Windows, send Ctrl+C is tricky with subprocess
            # Try taskkill without /F first
            result = subprocess.run(
                ["taskkill", "/PID", str(pid)],
                capture_output=True,
                timeout=timeout
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _force_stop(self, pid: int) -> bool:
        """Force kill a process.
        
        Args:
            pid: Process ID
            
        Returns:
            True if process killed
        """
        try:
            result = subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if a process is running.
        
        Args:
            pid: Process ID
            
        Returns:
            True if process exists
        """
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
                capture_output=True,
                text=True,
                encoding="gbk",
                errors="ignore"
            )
            return str(pid) in result.stdout
        except Exception:
            return False
    
    def _load_state(self) -> None:
        """Load state from file."""
        if not self._state_file.exists():
            return
        
        try:
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
            for item in data:
                # Convert workspace string to Path
                if item.get("workspace"):
                    item["workspace"] = Path(item["workspace"])
                # Convert started_at string to datetime
                if isinstance(item.get("started_at"), str):
                    from datetime import datetime
                    item["started_at"] = datetime.fromisoformat(item["started_at"])
                
                device = RunningDevice.model_validate(item)
                self._devices[device.name] = device
        except (json.JSONDecodeError, Exception):
            # If state file is corrupt, start fresh
            self._devices = {}
    
    def _save_state(self) -> None:
        """Save state to file."""
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = []
            for device in self._devices.values():
                item = device.model_dump()
                # Convert Path to string for JSON
                if item.get("workspace"):
                    item["workspace"] = str(item["workspace"])
                # Convert datetime to ISO string
                if hasattr(item["started_at"], "isoformat"):
                    item["started_at"] = item["started_at"].isoformat()
                data.append(item)
            
            self._state_file.write_text(
                json.dumps(data, indent=2),
                encoding="utf-8"
            )
        except Exception:
            # Fail silently - state is not critical
            pass


# Global instance for convenience
_default_manager: ProcessManager | None = None


def get_manager() -> ProcessManager:
    """Get the default process manager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = ProcessManager()
    return _default_manager
