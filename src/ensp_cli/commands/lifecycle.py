"""Lifecycle commands for device management."""

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from ensp_cli.models.running_device import RunningDevice
from ensp_cli.services.device_launcher import DeviceLauncher
from ensp_cli.services.process_manager import ProcessManager
from ensp_cli.services.topo_sync import TopoSyncService
from ensp_cli.services.coordinate_allocator import CoordinateAllocator
from ensp_cli.services.port_allocator import PortAllocator
from ensp_cli.services.mac_generator import MacGenerator

app = typer.Typer(help="Device lifecycle management commands")
console = Console()

# Default device limits
MAX_DEVICES_DEFAULT = 10


def _check_device_limit(process_manager: ProcessManager, max_devices: int = MAX_DEVICES_DEFAULT) -> bool:
    """Check if device limit reached.
    
    Args:
        process_manager: Process manager instance
        max_devices: Maximum allowed devices
        
    Returns:
        True if under limit
    """
    active_count = len(process_manager.list_devices(active_only=True))
    if active_count >= max_devices:
        console.print(f"[ERROR] Device limit reached ({max_devices}). Stop some devices first.", style="red")
        console.print(f"        Use 'ensp-cli ps' to see running devices.")
        console.print(f"        Use 'ensp-cli stop-device <name>' to stop a device.")
        return False
    return True


def _check_device_running(process_manager: ProcessManager, name: str) -> Optional[RunningDevice]:
    """Check if device is already running.
    
    Args:
        process_manager: Process manager instance
        name: Device name
        
    Returns:
        Existing device if running, None otherwise
    """
    existing = process_manager.get_device(name)
    if existing and existing.is_active():
        console.print(f"[ERROR] Device '{name}' is already running (PID: {existing.pid})", style="red")
        console.print(f"        Use 'ensp-cli stop-device {name}' first, or choose a different name.")
        return existing
    return None


def _find_topology_file(topo_file: Optional[Path]) -> Optional[Path]:
    """Find topology file.
    
    Args:
        topo_file: Explicit topology file path
        
    Returns:
        Path to topology file, or None if not found
    """
    if topo_file:
        return topo_file if topo_file.exists() else None
    
    # Auto-discover .topo files in current directory
    candidates = list(Path.cwd().glob("*.topo"))
    if len(candidates) == 1:
        return candidates[0]
    elif len(candidates) > 1:
        console.print("[WARNING] Multiple .topo files found. Please specify with --topology.", style="yellow")
        return None
    
    return None


def _map_device_type(device_type: str, model: str) -> tuple[str, str] | None:
    """Map topology device type to CLI type and model.
    
    Args:
        device_type: Device type from topology (may be empty)
        model: Device model from topology
        
    Returns:
        (device_type, model) tuple, or None if device should be skipped
    """
    if not model:
        return None
    
    model_lower = model.lower()
    type_lower = (device_type or "").lower()
    
    # Skip non-device types (Cloud, etc.)
    if "cloud" in model_lower:
        return None
    
    # Map by model - preserve original model name if it's a category
    if model_lower == "router":
        # Generic router category from eNSP GUI
        return ("router", "Router")
    elif "ar2220" in model_lower:
        return ("router", "AR2220")
    elif "ar3260" in model_lower:
        return ("router", "AR3260")
    elif model_lower == "switch":
        # Generic switch category from eNSP GUI
        return ("switch", "Switch")
    elif "s5700" in model_lower:
        return ("switch", "S5700")
    elif "s3700" in model_lower:
        return ("switch", "S3700")
    elif "lsw" in type_lower:
        return ("switch", "S5700")
    
    # Unknown device type, skip
    return None


@app.command(name="launch-router")
def launch_router_command(
    name: str = typer.Argument(..., help="Device name"),
    model: str = typer.Option("AR2220", "--model", "-m", help="Router model (AR2220, AR3260)"),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Console port (auto if not specified)"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t", help="Topology file to update"),
    timeout: int = typer.Option(30, "--timeout", help="Seconds to wait for device ready"),
    update_topo: bool = typer.Option(True, "--update-topo/--no-update-topo", help="Update topology file"),
    x: Optional[int] = typer.Option(None, "--x", help="X coordinate in topology (auto if not specified)"),
    y: Optional[int] = typer.Option(None, "--y", help="Y coordinate in topology (auto if not specified)"),
    max_devices: int = typer.Option(MAX_DEVICES_DEFAULT, "--max-devices", help="Maximum concurrent devices"),
) -> None:
    """Launch a router device."""
    # Initialize services
    process_manager = ProcessManager()
    
    # Check device limit
    if not _check_device_limit(process_manager, max_devices):
        raise typer.Exit(1)
    
    # Check if device already running
    if _check_device_running(process_manager, name):
        raise typer.Exit(1)
    
    # Launch device
    console.print(f"Launching router {name} ({model})...")
    
    launcher = DeviceLauncher()
    
    try:
        result = launcher.launch_router(name, model, port)
    except RuntimeError as e:
        console.print(f"[ERROR] Failed to launch device: {e}", style="red")
        raise typer.Exit(1)
    
    # Wait for readiness
    console.print(f"  Waiting for device to be ready (timeout: {timeout}s)...")
    
    async def wait_and_update():
        ready_result = await launcher.wait_for_ready(result["port"], timeout)
        return ready_result
    
    ready_result = asyncio.run(wait_and_update())
    
    if not ready_result["ready"]:
        console.print(f"[WARNING] Device may not be fully ready yet.", style="yellow")
    
    # Register device
    device = RunningDevice(
        name=name,
        device_type="router",
        model=model,
        pid=result["pid"],
        port=result["port"],
        mac_address=result["mac"],
        status="running" if ready_result["ready"] else "starting",
    )
    
    process_manager.register_device(device)
    
    # Update topology if requested
    topo_updated = False
    if update_topo:
        topo_path = _find_topology_file(topo_file)
        if topo_path:
            sync_service = TopoSyncService()
            try:
                sync_result = sync_service.add_device_to_topo(
                    topo_path, device, custom_cx=x, custom_cy=y
                )
                if sync_result["success"]:
                    topo_updated = True
            except Exception as e:
                console.print(f"[WARNING] Failed to update topology: {e}", style="yellow")
    
    # Display success
    console.print(f"[OK] Launched router {name} ({model})", style="green")
    console.print(f"     Console: telnet 127.0.0.1:{result['port']}")
    console.print(f"     MAC: {result['mac']}")
    console.print(f"     PID: {result['pid']}")
    if device.cx is not None and device.cy is not None:
        console.print(f"     Position: ({device.cx}, {device.cy})")
    if topo_updated:
        console.print(f"     Topology updated: {topo_path.name}")


@app.command(name="launch-switch")
def launch_switch_command(
    name: str = typer.Argument(..., help="Device name"),
    model: str = typer.Option("S5700", "--model", "-m", help="Switch model (S3700, S5700)"),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Console port (auto if not specified)"),
    topo_file: Optional[Path] = typer.Option(None, "--topology", "-t", help="Topology file to update"),
    timeout: int = typer.Option(30, "--timeout", help="Seconds to wait for device ready"),
    update_topo: bool = typer.Option(True, "--update-topo/--no-update-topo", help="Update topology file"),
    x: Optional[int] = typer.Option(None, "--x", help="X coordinate in topology (auto if not specified)"),
    y: Optional[int] = typer.Option(None, "--y", help="Y coordinate in topology (auto if not specified)"),
    max_devices: int = typer.Option(MAX_DEVICES_DEFAULT, "--max-devices", help="Maximum concurrent devices"),
) -> None:
    """Launch a switch device."""
    # Initialize services
    process_manager = ProcessManager()
    
    # Check device limit
    if not _check_device_limit(process_manager, max_devices):
        raise typer.Exit(1)
    
    # Check if device already running
    if _check_device_running(process_manager, name):
        raise typer.Exit(1)
    
    # Launch device
    console.print(f"Launching switch {name} ({model})...")
    
    launcher = DeviceLauncher()
    
    try:
        result = launcher.launch_switch(name, model, port)
    except RuntimeError as e:
        console.print(f"[ERROR] Failed to launch device: {e}", style="red")
        raise typer.Exit(1)
    
    # Wait for readiness
    console.print(f"  Waiting for device to be ready (timeout: {timeout}s)...")
    
    async def wait_and_update():
        ready_result = await launcher.wait_for_ready(result["port"], timeout)
        return ready_result
    
    ready_result = asyncio.run(wait_and_update())
    
    if not ready_result["ready"]:
        console.print(f"[WARNING] Device may not be fully ready yet.", style="yellow")
    
    # Register device
    device = RunningDevice(
        name=name,
        device_type="switch",
        model=model,
        pid=result["pid"],
        port=result["port"],
        mac_address=result["mac"],
        status="running" if ready_result["ready"] else "starting",
    )
    
    process_manager.register_device(device)
    
    # Update topology if requested
    topo_updated = False
    if update_topo:
        topo_path = _find_topology_file(topo_file)
        if topo_path:
            sync_service = TopoSyncService()
            try:
                sync_result = sync_service.add_device_to_topo(
                    topo_path, device, custom_cx=x, custom_cy=y
                )
                if sync_result["success"]:
                    topo_updated = True
            except Exception as e:
                console.print(f"[WARNING] Failed to update topology: {e}", style="yellow")
    
    # Display success
    console.print(f"[OK] Launched switch {name} ({model})", style="green")
    console.print(f"     Console: telnet 127.0.0.1:{result['port']}")
    console.print(f"     MAC: {result['mac']}")
    console.print(f"     PID: {result['pid']}")
    if device.cx is not None and device.cy is not None:
        console.print(f"     Position: ({device.cx}, {device.cy})")
    if topo_updated:
        console.print(f"     Topology updated: {topo_path.name}")


@app.command(name="stop-device")
def stop_device_command(
    name: Optional[str] = typer.Argument(None, help="Device name to stop"),
    force: bool = typer.Option(False, "--force", "-f", help="Force kill if graceful stop fails"),
    all_devices: bool = typer.Option(False, "--all", "-a", help="Stop all running devices"),
) -> None:
    """Stop a running device."""
    process_manager = ProcessManager()
    
    if all_devices:
        devices = process_manager.list_devices(active_only=True)
        if not devices:
            console.print("[OK] No running devices to stop.", style="green")
            return
        
        console.print(f"Stopping {len(devices)} device(s)...")
        for device in devices:
            result = process_manager.stop_device(device.name, force)
            if result["success"]:
                console.print(f"  [OK] {device.name}: {result['message']}", style="green")
            else:
                console.print(f"  [ERROR] {device.name}: {result['message']}", style="red")
    
    else:
        if not name:
            console.print("[ERROR] Please specify device name or use --all", style="red")
            raise typer.Exit(1)
        
        result = process_manager.stop_device(name, force)
        
        if result["success"]:
            console.print(f"[OK] {result['message']}", style="green")
        else:
            console.print(f"[ERROR] {result['message']}", style="red")
            raise typer.Exit(1)


@app.command(name="ps")
def ps_command(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table, json"),
    refresh: bool = typer.Option(True, "--refresh/--no-refresh", help="Refresh status before display"),
) -> None:
    """List running devices."""
    process_manager = ProcessManager()
    devices = process_manager.list_devices(refresh=refresh)
    
    # Also detect GUI devices
    sync_service = TopoSyncService()
    gui_devices = sync_service.get_gui_devices()
    
    # Filter out GUI devices that are already tracked
    tracked_pids = {d.pid for d in devices}
    new_gui_devices = [d for d in gui_devices if d["pid"] not in tracked_pids]
    
    if output.lower() == "json":
        # JSON output
        data = {
            "cli_devices": [
                {
                    "name": d.name,
                    "type": d.device_type,
                    "model": d.model,
                    "port": d.port,
                    "status": d.status,
                    "uptime": d.get_uptime_str(),
                    "pid": d.pid,
                }
                for d in devices
            ],
            "gui_devices": [
                {
                    "type": d["device_type"],
                    "ports": d["ports"],
                    "pid": d["pid"],
                    "source": "gui",
                }
                for d in new_gui_devices
            ],
        }
        console.print(json.dumps(data, indent=2))
    else:
        # Table output
        if devices:
            table = Table(title="CLI-Managed Devices", box=box.SIMPLE)
            table.add_column("NAME", style="cyan")
            table.add_column("TYPE", style="green")
            table.add_column("MODEL")
            table.add_column("PORT", justify="right")
            table.add_column("STATUS")
            table.add_column("UPTIME")
            
            for device in devices:
                status_style = "green" if device.status == "running" else "yellow"
                table.add_row(
                    device.name,
                    device.device_type,
                    device.model,
                    str(device.port),
                    f"[{status_style}]{device.status}[/{status_style}]",
                    device.get_uptime_str(),
                )
            
            console.print(table)
        
        if new_gui_devices:
            gui_table = Table(title="GUI-Managed Devices (detected)", box=box.SIMPLE)
            gui_table.add_column("TYPE", style="green")
            gui_table.add_column("PID", justify="right")
            gui_table.add_column("PORTS")
            
            for device in new_gui_devices:
                gui_table.add_row(
                    device["device_type"],
                    str(device["pid"]),
                    ", ".join(str(p) for p in device["ports"][:3]) + ("..." if len(device["ports"]) > 3 else ""),
                )
            
            console.print(gui_table)
        
        if not devices and not new_gui_devices:
            console.print("[OK] No running devices found.", style="green")


@app.command(name="launch-topology")
def launch_topology_command(
    topo_file: Optional[Path] = typer.Argument(None, help="Topology file (auto-discover if not specified)"),
    timeout: int = typer.Option(60, "--timeout", help="Timeout per device"),
    parallel: bool = typer.Option(True, "--parallel/--sequential", help="Launch devices in parallel"),
    max_devices: int = typer.Option(MAX_DEVICES_DEFAULT, "--max-devices", help="Maximum concurrent devices"),
) -> None:
    """Launch all devices from a topology file."""
    # Find topology file
    topo_path = _find_topology_file(topo_file)
    
    if not topo_path:
        if topo_file:
            console.print(f"[ERROR] Topology file not found: {topo_file}", style="red")
        else:
            console.print("[ERROR] No topology file found. Please specify with --topology.", style="red")
        raise typer.Exit(1)
    
    # Parse topology
    sync_service = TopoSyncService()
    
    try:
        root = sync_service.load_topology(topo_path)
    except Exception as e:
        console.print(f"[ERROR] Failed to load topology: {e}", style="red")
        raise typer.Exit(1)
    
    # Find devices in topology
    devices_elem = root.find("devices")
    if devices_elem is None:
        console.print("[ERROR] No devices found in topology.", style="red")
        raise typer.Exit(1)
    
    topo_devices = devices_elem.findall("dev")
    if not topo_devices:
        console.print("[OK] No devices to launch in topology.", style="green")
        return
    
    # Check device limit
    process_manager = ProcessManager()
    current_count = len(process_manager.list_devices(active_only=True))
    available_slots = max_devices - current_count
    
    if available_slots <= 0:
        console.print(f"[ERROR] Device limit reached ({max_devices}). Stop some devices first.", style="red")
        raise typer.Exit(1)
    
    # Limit devices if needed
    if len(topo_devices) > available_slots:
        console.print(f"[WARNING] Can only launch {available_slots} of {len(topo_devices)} devices due to limit.", style="yellow")
        topo_devices = topo_devices[:available_slots]
    
    console.print(f"Launching {len(topo_devices)} device(s) from {topo_path.name}...")
    console.print()
    
    # Launch devices
    launcher = DeviceLauncher()
    launched = []
    failed = []
    
    for dev_elem in topo_devices:
        dev_name = dev_elem.get("name", "")
        dev_type = dev_elem.get("device_type", "")
        dev_model = dev_elem.get("model", "")
        
        if not dev_name:
            continue
        
        # Check if already running
        if process_manager.get_device(dev_name):
            console.print(f"  {dev_name}: Already running, skipping")
            continue
        
        # Map device type
        mapped = _map_device_type(dev_type, dev_model)
        if mapped is None:
            console.print(f"  {dev_name}: Skipping (unsupported: type={dev_type}, model={dev_model})")
            continue
        
        device_type, model = mapped
        
        # Launch
        try:
            if device_type == "router":
                result = launcher.launch_router(dev_name, model)
            else:
                result = launcher.launch_switch(dev_name, model)
            
            # Register
            device = RunningDevice(
                name=dev_name,
                device_type=device_type,
                model=model,
                pid=result["pid"],
                port=result["port"],
                mac_address=result["mac"],
                status="starting",
            )
            process_manager.register_device(device)
            launched.append(device)
            console.print(f"  [OK] {dev_name} ({model}) - Port {result['port']}", style="green")
            
        except Exception as e:
            failed.append((dev_name, str(e)))
            console.print(f"  [ERROR] {dev_name}: {e}", style="red")
    
    # Summary
    console.print()
    console.print(f"Launched: {len(launched)} device(s)")
    if failed:
        console.print(f"Failed: {len(failed)} device(s)", style="red")
